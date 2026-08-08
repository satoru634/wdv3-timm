import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import timm
import torch
from huggingface_hub import hf_hub_download
from huggingface_hub.utils import HfHubHTTPError
from PIL import Image
from timm.data import create_transform, resolve_data_config
from torch import Tensor, nn
from torch.nn import functional as F

torch_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_REPO_MAP = {
    "vit": "SmilingWolf/wd-vit-tagger-v3",
    "swinv2": "SmilingWolf/wd-swinv2-tagger-v3",
    "convnext": "SmilingWolf/wd-convnext-tagger-v3",
    "eva02": "SmilingWolf/wd-eva02-large-tagger-v3",
    "vit-large": "SmilingWolf/wd-vit-large-tagger-v3",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


def pil_ensure_rgb(image: Image.Image) -> Image.Image:
    # convert to RGB/RGBA if not already (deals with palette images etc.)
    if image.mode not in ["RGB", "RGBA"]:
        image = image.convert("RGBA") if "transparency" in image.info else image.convert("RGB")
    # convert RGBA to RGB with white background
    if image.mode == "RGBA":
        canvas = Image.new("RGBA", image.size, (255, 255, 255))
        canvas.alpha_composite(image)
        image = canvas.convert("RGB")
    return image


def pil_pad_square(image: Image.Image) -> Image.Image:
    w, h = image.size
    # get the largest dimension so we can pad to a square
    px = max(image.size)
    # pad to square with white background
    canvas = Image.new("RGB", (px, px), (255, 255, 255))
    canvas.paste(image, ((px - w) // 2, (px - h) // 2))
    return canvas


def find_image_files(directory: Path) -> list[Path]:
    # ディレクトリ配下（サブディレクトリを含む）の画像ファイルをパスの昇順で取得する
    files = [p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
    return sorted(files)


@dataclass
class LabelData:
    names: list[str]
    rating: list[np.int64]
    general: list[np.int64]
    character: list[np.int64]


def load_labels_hf(
    repo_id: str,
    revision: Optional[str] = None,
    token: Optional[str] = None,
) -> LabelData:
    try:
        csv_path = hf_hub_download(
            repo_id=repo_id, filename="selected_tags.csv", revision=revision, token=token
        )
        csv_path = Path(csv_path).resolve()
    except HfHubHTTPError as e:
        raise FileNotFoundError(f"selected_tags.csv failed to download from {repo_id}") from e

    df: pd.DataFrame = pd.read_csv(csv_path, usecols=["name", "category"])
    tag_data = LabelData(
        names=df["name"].tolist(),
        rating=list(np.where(df["category"] == 9)[0]),
        general=list(np.where(df["category"] == 0)[0]),
        character=list(np.where(df["category"] == 4)[0]),
    )

    return tag_data


def get_tags(
    probs: Tensor,
    labels: LabelData,
    gen_threshold: float,
    char_threshold: float,
):
    # Convert indices+probs to labels
    probs = list(zip(labels.names, probs.numpy()))

    # First 4 labels are actually ratings
    rating_labels = dict([probs[i] for i in labels.rating])

    # General labels, pick any where prediction confidence > threshold
    gen_labels = [probs[i] for i in labels.general]
    gen_labels = dict([x for x in gen_labels if x[1] > gen_threshold])
    gen_labels = dict(sorted(gen_labels.items(), key=lambda item: item[1], reverse=True))

    # Character labels, pick any where prediction confidence > threshold
    char_labels = [probs[i] for i in labels.character]
    char_labels = dict([x for x in char_labels if x[1] > char_threshold])
    char_labels = dict(sorted(char_labels.items(), key=lambda item: item[1], reverse=True))

    # Combine general and character labels, sort by confidence
    combined_names = [x for x in gen_labels]
    combined_names.extend([x for x in char_labels])

    # Convert to a string suitable for use as a training caption
    caption = ", ".join(combined_names)
    taglist = caption.replace("_", " ").replace("(", "\\(").replace(")", "\\)")

    return caption, taglist, rating_labels, char_labels, gen_labels


@dataclass
class ScriptOptions:
    input_path: Path
    model: str = "vit"
    gen_threshold: float = 0.35
    char_threshold: float = 0.75
    output: Optional[Path] = None


def parse_args() -> ScriptOptions:
    parser = argparse.ArgumentParser(description="WD Tagger V3 で画像にタグ付けを行う")
    parser.add_argument(
        "-i", "--input",
        type=Path,
        required=True,
        help="タグ付け対象の画像ファイル、またはディレクトリのパス"
        "（ディレクトリの場合はサブディレクトリも含めて再帰的に処理する）",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="vit",
        choices=list(MODEL_REPO_MAP.keys()),
        help="使用するモデル名（デフォルト: vit）",
    )
    parser.add_argument(
        "--gen_threshold", "-g",
        type=float,
        default=0.35,
        help="一般タグの閾値（デフォルト: 0.35）",
    )
    parser.add_argument(
        "--char_threshold", "-c",
        type=float,
        default=0.75,
        help="キャラクタータグの閾値（デフォルト: 0.75）",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="結果をJSON形式で保存するファイルパス"
        "（ディレクトリを処理した場合は全画像分の結果を配列としてまとめて保存する。"
        "指定しない場合は標準出力にテキスト表示）",
    )
    args = parser.parse_args()
    return ScriptOptions(
        input_path=args.input,
        model=args.model,
        gen_threshold=args.gen_threshold,
        char_threshold=args.char_threshold,
        output=args.output,
    )


def show_results(
    caption: str,
    taglist: str,
    ratings: dict[str, float],
    character: dict[str, float],
    general: dict[str, float],
    opts: ScriptOptions,
    image_path: Optional[Path] = None,
) -> None:
    if image_path is not None:
        print(f"===== {image_path} =====")
    print("--------")
    print(f"Caption: {caption}")
    print("--------")
    print(f"Tags: {taglist}")

    print("--------")
    print("Ratings:")
    for k, v in ratings.items():
        print(f"  {k}: {v:.3f}")

    print("--------")
    print(f"Character tags (threshold={opts.char_threshold}):")
    for k, v in character.items():
        print(f"  {k}: {v:.3f}")

    print("--------")
    print(f"General tags (threshold={opts.gen_threshold}):")
    for k, v in general.items():
        print(f"  {k}: {v:.3f}")

    print("Done!")


def build_result_dict(
    image_path: Path,
    caption: str,
    taglist: str,
    ratings: dict[str, float],
    character: dict[str, float],
    general: dict[str, float],
    opts: ScriptOptions,
) -> dict:
    return {
        "image_file": str(image_path),
        "model": opts.model,
        "caption": caption,
        "tags": taglist,
        "thresholds": {
            "general": opts.gen_threshold,
            "character": opts.char_threshold,
        },
        "ratings": {k: float(v) for k, v in ratings.items()},
        "character": {k: float(v) for k, v in character.items()},
        "general": {k: float(v) for k, v in general.items()},
    }


def save_results_json(results: list[dict], opts: ScriptOptions) -> None:
    # 画像1件のみの場合は従来通りオブジェクト、複数件の場合は配列として保存する
    output_data = results[0] if len(results) == 1 else results

    opts.output.parent.mkdir(parents=True, exist_ok=True)
    with open(opts.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"結果をJSONファイルに保存しました: {opts.output}")


def process_image(
    image_path: Path,
    model: nn.Module,
    transform,
    labels: LabelData,
    opts: ScriptOptions,
):
    # get image
    img_input: Image.Image = Image.open(image_path)
    # ensure image is RGB
    img_input = pil_ensure_rgb(img_input)
    # pad to square with white background
    img_input = pil_pad_square(img_input)
    # run the model's input transform to convert to tensor and rescale
    inputs: Tensor = transform(img_input).unsqueeze(0)
    # NCHW image RGB to BGR
    inputs = inputs[:, [2, 1, 0]]

    with torch.inference_mode():
        if torch_device.type != "cpu":
            inputs = inputs.to(torch_device)
        # run the model
        outputs = model.forward(inputs)
        # apply the final activation function (timm doesn't support doing this internally)
        outputs = F.sigmoid(outputs)
        if torch_device.type != "cpu":
            outputs = outputs.to("cpu")

    return get_tags(
        probs=outputs.squeeze(0),
        labels=labels,
        gen_threshold=opts.gen_threshold,
        char_threshold=opts.char_threshold,
    )


def main(opts: ScriptOptions):
    repo_id = MODEL_REPO_MAP.get(opts.model)
    input_path = Path(opts.input_path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    if input_path.is_dir():
        image_paths = find_image_files(input_path)
        if not image_paths:
            raise FileNotFoundError(f"No image files found in directory: {input_path}")
    else:
        image_paths = [input_path]

    print(f"Loading model '{opts.model}' from '{repo_id}'...")
    model: nn.Module = timm.create_model("hf-hub:" + repo_id).eval()
    state_dict = timm.models.load_state_dict_from_hf(repo_id)
    model.load_state_dict(state_dict)
    # move model to GPU, if available
    if torch_device.type != "cpu":
        model = model.to(torch_device)

    print("Loading tag list...")
    labels: LabelData = load_labels_hf(repo_id=repo_id)

    print("Creating data transform...")
    transform = create_transform(**resolve_data_config(model.pretrained_cfg, model=model))

    is_multiple = len(image_paths) > 1
    result_dicts = []
    for i, image_path in enumerate(image_paths, start=1):
        print(f"[{i}/{len(image_paths)}] '{image_path.name}' を処理中...")
        caption, taglist, ratings, character, general = process_image(
            image_path, model, transform, labels, opts
        )

        if opts.output is not None:
            result_dicts.append(
                build_result_dict(image_path, caption, taglist, ratings, character, general, opts)
            )
        else:
            show_results(
                caption, taglist, ratings, character, general, opts,
                image_path=image_path if is_multiple else None,
            )

    if opts.output is not None:
        save_results_json(result_dicts, opts)


if __name__ == "__main__":
    opts = parse_args()
    main(opts)
