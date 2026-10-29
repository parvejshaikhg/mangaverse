"""
Chapter Exporter Engine.
Converts raw downloaded chapter images into organized folders, CBZ comic archives, or PDF books.
"""

from pathlib import Path
import shutil
import zipfile
from typing import Literal
from PIL import Image


class ChapterExporter:
    """
    Handles packaging of chapter images into user-selected distribution formats:
    - CBZ (Comic Book Zip - standard for comic readers like Tachiyomi, Panels, CDisplayEx)
    - PDF (Portable Document Format - convenient for reading on phones, tablets, or Acrobat)
    - Raw Images (Folder containing sequentially numbered image files)
    """

    @staticmethod
    def export(
        temp_dir: Path,
        destination_folder: Path,
        file_stem: str,
        export_format: Literal["cbz", "pdf", "images"] = "cbz",
    ) -> Path:
        """
        Exports the downloaded images from temp_dir to destination_folder in the specified format.
        Returns the path to the resulting file or folder.
        """
        destination_folder.mkdir(parents=True, exist_ok=True)
        images = sorted(
            [f for f in temp_dir.iterdir() if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]]
        )

        if not images:
            raise ValueError(f"No valid image files found in {temp_dir} to export.")

        if export_format == "cbz":
            target_path = destination_folder / f"{file_stem}.cbz"
            ChapterExporter._build_cbz(images, target_path)
            return target_path

        elif export_format == "pdf":
            target_path = destination_folder / f"{file_stem}.pdf"
            ChapterExporter._build_pdf(images, target_path)
            return target_path

        else:  # "images"
            target_dir = destination_folder / file_stem
            target_dir.mkdir(parents=True, exist_ok=True)
            for idx, img_path in enumerate(images, start=1):
                extension = img_path.suffix.lower()
                target_file = target_dir / f"{idx:03d}{extension}"
                shutil.copy2(img_path, target_file)
            return target_dir

    @staticmethod
    def _build_cbz(image_paths: list[Path], target_cbz: Path) -> None:
        """Packs image files into a compressed CBZ (ZIP) comic container."""
        # Use a temporary file first for atomic writes
        temp_zip = target_cbz.with_suffix(".tmp.cbz")
        try:
            with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for idx, img in enumerate(image_paths, start=1):
                    archive_name = f"{idx:03d}{img.suffix.lower()}"
                    zf.write(img, arcname=archive_name)
            
            # Atomic rename to prevent corrupt incomplete files
            if target_cbz.exists():
                target_cbz.unlink()
            temp_zip.rename(target_cbz)
        finally:
            if temp_zip.exists():
                temp_zip.unlink()

    @staticmethod
    def _build_pdf(image_paths: list[Path], target_pdf: Path) -> None:
        """Merges multiple image files into a single unified PDF."""
        temp_pdf = target_pdf.with_suffix(".tmp.pdf")
        pil_images: list[Image.Image] = []

        try:
            for img_path in image_paths:
                img = Image.open(img_path)
                # Convert RGBA / P mode images to RGB for PDF compatibility
                if img.mode != "RGB":
                    img = img.convert("RGB")
                pil_images.append(img)

            if not pil_images:
                raise ValueError("No images loaded for PDF creation.")

            first_page = pil_images[0]
            remaining_pages = pil_images[1:] if len(pil_images) > 1 else []

            first_page.save(
                temp_pdf,
                format="PDF",
                save_all=True,
                append_images=remaining_pages,
                resolution=100.0,
            )

            # Close file handles
            for img in pil_images:
                try:
                    img.close()
                except Exception:
                    pass

            if target_pdf.exists():
                target_pdf.unlink()
            temp_pdf.rename(target_pdf)
        finally:
            for img in pil_images:
                try:
                    img.close()
                except Exception:
                    pass
            if temp_pdf.exists():
                temp_pdf.unlink()
