import json
import os
import tkinter as tk
from copy import deepcopy
from fractions import Fraction
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk
from PIL.ExifTags import GPSTAGS, TAGS


LABELS = [
    "담배꽁초",
    "종이류",
    "플라스틱류",
    "비닐류",
    "캔/금속류",
    "유리류",
    "스티로폼",
    "일반쓰레기",
    "대형/수거불가",
]

SIZE_OPTIONS = ["small", "medium", "large"]

SIZE_GUIDE = {
    "small": "소: 손바닥 이하, 한 손으로 쉽게 집을 수 있음",
    "medium": "중: 한 손 또는 양손으로 들 수 있으나 비교적 부피가 있음",
    "large": "대: 도보 수거가 어렵거나 부피가 큼",
}

DEFAULT_CANVAS_W = 1100
DEFAULT_CANVAS_H = 780

# 기본 경로 설정
# JSON 파일은 메타데이터를 읽고, 같은 파일에 라벨 결과를 저장합니다.
DEFAULT_IMAGE_DIRS = []
DEFAULT_JSON_PATH = ""
STATE_FILE = ".plogging_labeling_state.json"


def _rational_to_float(value):
    if isinstance(value, Fraction):
        return float(value)
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        return float(value.numerator) / float(value.denominator)
    if isinstance(value, tuple) and len(value) == 2:
        return float(value[0]) / float(value[1])
    return float(value)


def _dms_to_decimal(values, ref):
    degrees = _rational_to_float(values[0])
    minutes = _rational_to_float(values[1])
    seconds = _rational_to_float(values[2])
    result = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if ref in {"S", "W"}:
        result *= -1
    return result


class PloggingLabelingTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Plogging Image Labeling Tool")
        self.root.geometry("1600x920")
        self.root.minsize(1280, 820)

        self.image_dirs = list(DEFAULT_IMAGE_DIRS)
        self.json_paths = [DEFAULT_JSON_PATH] if DEFAULT_JSON_PATH else []
        self.json_path = DEFAULT_JSON_PATH
        self.read_only_mode = False

        self.records = []
        self.output_records = []
        self.current_index = -1
        self.current_record = None
        self.state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), STATE_FILE)

        self.original_image = None
        self.tk_image = None
        self.display_scale = 1.0
        self.display_offset_x = 0
        self.display_offset_y = 0
        self.display_w = 0
        self.display_h = 0

        self.selected_item_index = None

        self._build_ui()
        self._bind_shortcuts()
        self._apply_saved_paths()

    def _build_ui(self):
        outer = tk.Frame(self.root)
        outer.pack(fill="both", expand=True)

        left = tk.Frame(outer, padx=8, pady=8)
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(outer, width=430, padx=8, pady=8)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        topbar = tk.LabelFrame(left, text="경로 설정", padx=8, pady=8)
        topbar.pack(fill="x")

        self.image_dir_var = tk.StringVar(value="; ".join(self.image_dirs))
        self.json_path_var = tk.StringVar(value="; ".join(self.json_paths))

        self._path_row(topbar, 0, "이미지 폴더들", self.image_dir_var, self.select_image_dirs)
        self._path_row(topbar, 1, "JSON 파일들", self.json_path_var, self.select_json_paths)

        btn_row = tk.Frame(topbar)
        btn_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        tk.Button(btn_row, text="불러오기", command=self.load_project, width=12).pack(side="left")
        tk.Button(btn_row, text="저장", command=self.save_output, width=12).pack(side="left", padx=6)
        tk.Button(btn_row, text="빈 항목으로 초기화", command=self.clear_current_items, width=16).pack(side="left")

        self.progress_var = tk.StringVar(value="데이터를 불러오세요.")
        tk.Label(topbar, textvariable=self.progress_var, anchor="w").grid(
            row=3, column=0, columnspan=3, sticky="ew", pady=(8, 0)
        )

        nav = tk.Frame(left, pady=8)
        nav.pack(fill="x")
        tk.Button(nav, text="이전", command=self.prev_record, width=10).pack(side="left")
        tk.Button(nav, text="현재 저장", command=self.save_current_record, width=12).pack(side="left")
        tk.Button(nav, text="저장 후 다음", command=self.save_and_next_record, width=14).pack(side="left", padx=6)

        self.record_title_var = tk.StringVar(value="현재 항목 없음")
        tk.Label(nav, textvariable=self.record_title_var, anchor="w").pack(side="left", padx=12)

        canvas_frame = tk.LabelFrame(left, text="이미지 보기", padx=6, pady=6)
        canvas_frame.pack(fill="both", expand=True, pady=(0, 0))

        self.canvas = tk.Canvas(canvas_frame, width=DEFAULT_CANVAS_W, height=DEFAULT_CANVAS_H, bg="#222")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.on_canvas_resize)

        info_box = tk.LabelFrame(right, text="메타 정보", padx=8, pady=8)
        info_box.pack(fill="x")

        self.meta_text = tk.Text(info_box, height=13, wrap="word")
        self.meta_text.pack(fill="x")
        self.meta_text.configure(state="disabled")

        item_box = tk.LabelFrame(right, text="쓰레기 항목 입력", padx=8, pady=8)
        item_box.pack(fill="x", pady=(8, 0))

        tk.Label(item_box, text="label").grid(row=0, column=0, sticky="w")
        self.label_var = tk.StringVar(value=LABELS[0])
        self.label_combo = ttk.Combobox(item_box, values=LABELS, textvariable=self.label_var, state="readonly")
        self.label_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        tk.Label(item_box, text="size").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.size_var = tk.StringVar(value=SIZE_OPTIONS[0])
        self.size_combo = ttk.Combobox(item_box, values=SIZE_OPTIONS, textvariable=self.size_var, state="readonly")
        self.size_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))

        tk.Label(item_box, text="quantity").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.quantity_var = tk.StringVar(value="1")
        tk.Spinbox(item_box, from_=1, to=999, textvariable=self.quantity_var, width=10).grid(
            row=2, column=1, sticky="w", padx=(8, 0), pady=(8, 0)
        )

        item_box.grid_columnconfigure(1, weight=1)

        self.size_guide_var = tk.StringVar(value=SIZE_GUIDE[self.size_var.get()])
        tk.Label(item_box, textvariable=self.size_guide_var, fg="#444", wraplength=360, justify="left").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        self.size_combo.bind("<<ComboboxSelected>>", lambda e: self.size_guide_var.set(SIZE_GUIDE[self.size_var.get()]))

        item_btn_row = tk.Frame(item_box)
        item_btn_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        tk.Button(item_btn_row, text="항목 추가", command=self.add_item, width=12).pack(side="left")
        tk.Button(item_btn_row, text="선택 항목 수정", command=self.update_selected_item, width=14).pack(side="left", padx=6)
        tk.Button(item_btn_row, text="선택 항목 삭제", command=self.delete_selected_item, width=14).pack(side="left")

        itemlist_box = tk.LabelFrame(right, text="현재 이미지의 쓰레기 목록", padx=8, pady=8)
        itemlist_box.pack(fill="both", expand=True, pady=(8, 0))

        self.item_listbox = tk.Listbox(itemlist_box, height=18)
        self.item_listbox.pack(fill="both", expand=True)
        self.item_listbox.bind("<<ListboxSelect>>", self.on_select_item)

        guide_box = tk.LabelFrame(right, text="사용 방법", padx=8, pady=8)
        guide_box.pack(fill="x", pady=(8, 0))
        guide_text = (
            "1. 이미지 폴더와 JSON 파일 경로를 지정합니다.\n"
            "2. 불러오기를 누르면 JSON의 imagePath를 기준으로 이미지를 엽니다.\n"
            "3. JSON 파일이 없으면 이미지 폴더 기준으로 새 JSON을 생성합니다.\n"
            "4. 좌표나 시간이 비어 있으면 사진 EXIF에서 자동으로 채웁니다.\n"
            "5. 항목을 입력한 뒤 저장하거나 저장 후 다음으로 이동할 수 있습니다."
        )
        tk.Label(guide_box, text=guide_text, justify="left", wraplength=390).pack(anchor="w")

    def _bind_shortcuts(self):
        self.root.bind("<Return>", self._handle_enter_shortcut)
        self.root.bind("<Control-s>", self._handle_save_shortcut)
        self.root.bind("<Left>", self._handle_prev_shortcut)

    def _focus_on_text_input(self):
        widget = self.root.focus_get()
        return isinstance(widget, (tk.Entry, tk.Text, tk.Spinbox, ttk.Combobox))

    def _handle_enter_shortcut(self, event=None):
        if self._focus_on_text_input():
            return
        self.save_and_next_record()

    def _handle_save_shortcut(self, event=None):
        self.save_current_record()
        return "break"

    def _handle_prev_shortcut(self, event=None):
        if self._focus_on_text_input():
            return
        self.prev_record()

    def _path_row(self, parent, row, label, textvar, command):
        tk.Label(parent, text=label, width=10, anchor="w").grid(row=row, column=0, sticky="w", pady=3)
        tk.Entry(parent, textvariable=textvar).grid(row=row, column=1, sticky="ew", padx=6)
        tk.Button(parent, text="선택", command=command, width=10).grid(row=row, column=2, sticky="e")
        parent.grid_columnconfigure(1, weight=1)

    def _record_key(self, record):
        return (
            str(record.get("imagePath", "")),
            str(record.get("timestamp", "")),
            str(record.get("latitude", "")),
            str(record.get("longitude", "")),
        )

    def _parse_json_paths(self):
        raw = self.json_path_var.get().strip()
        if not raw:
            return []
        return [path.strip() for path in raw.split(";") if path.strip()]

    def _parse_image_dirs(self):
        raw = self.image_dir_var.get().strip()
        if not raw:
            return []
        return [path.strip() for path in raw.split(";") if path.strip()]

    def _set_image_dirs(self, paths):
        self.image_dirs = [path for path in paths if path]
        self.image_dir_var.set("; ".join(self.image_dirs))

    def _set_json_paths(self, paths):
        self.json_paths = [path for path in paths if path]
        self.json_path = self.json_paths[0] if len(self.json_paths) == 1 else ""
        self.json_path_var.set("; ".join(self.json_paths))

    def _ensure_editable(self):
        if self.read_only_mode:
            messagebox.showinfo("안내", "여러 JSON 파일을 병합해 연 상태에서는 편집과 저장을 할 수 없습니다.")
            return False
        return True

    def _merge_items(self, base_items, new_items):
        merged = list(base_items)
        seen = {
            (item.get("label", ""), item.get("size", ""), item.get("quantity", 1))
            for item in merged
            if isinstance(item, dict)
        }
        for item in new_items:
            if not isinstance(item, dict):
                continue
            key = (item.get("label", ""), item.get("size", ""), item.get("quantity", 1))
            if key in seen:
                continue
            merged.append(item)
            seen.add(key)
        return merged

    def _merge_record_lists(self, record_lists):
        merged_map = {}
        order = []
        for records in record_lists:
            for record in records:
                key = self._record_key(record)
                if key not in merged_map:
                    merged_map[key] = deepcopy(record)
                    order.append(key)
                    continue
                existing = merged_map[key]
                if existing.get("latitude") in (None, "") and record.get("latitude") not in (None, ""):
                    existing["latitude"] = record.get("latitude")
                if existing.get("longitude") in (None, "") and record.get("longitude") not in (None, ""):
                    existing["longitude"] = record.get("longitude")
                if not existing.get("timestamp") and record.get("timestamp"):
                    existing["timestamp"] = record.get("timestamp")
                existing["items"] = self._merge_items(existing.get("items", []), record.get("items", []))
        return [merged_map[key] for key in order]

    def _validated_quantity(self):
        raw = str(self.quantity_var.get()).strip()
        try:
            value = int(raw)
        except ValueError:
            messagebox.showwarning("경고", "quantity는 1 이상의 정수여야 합니다.")
            return None
        if value < 1:
            messagebox.showwarning("경고", "quantity는 1 이상의 정수여야 합니다.")
            return None
        return value

    def _replace_output_with_existing(self, existing_records):
        existing_map = {}
        for record in existing_records:
            existing_map[self._record_key(record)] = record

        merged = []
        for current in self.output_records:
            merged.append(existing_map.get(self._record_key(current), current))
        self.output_records = merged

    def _load_app_state(self):
        if not os.path.exists(self.state_path):
            return {}
        try:
            with open(self.state_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, dict):
                return data
        except Exception:
            return {}
        return {}

    def _save_app_state(self):
        payload = {
            "image_dirs": self.image_dirs,
            "json_paths": self.json_paths,
            "last_index": self.current_index,
        }
        try:
            with open(self.state_path, "w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _apply_saved_paths(self):
        state = self._load_app_state()
        if not self.image_dir_var.get():
            saved_dirs = state.get("image_dirs")
            if isinstance(saved_dirs, list):
                self._set_image_dirs(saved_dirs)
        if not self.json_path_var.get():
            saved_paths = state.get("json_paths")
            if isinstance(saved_paths, list):
                self._set_json_paths(saved_paths)

    def _get_initial_index(self):
        state = self._load_app_state()
        saved_paths = state.get("json_paths")
        saved_index = state.get("last_index")
        current_paths = [os.path.normpath(path) for path in self.json_paths]
        if isinstance(saved_paths, list):
            saved_paths = [os.path.normpath(path) for path in saved_paths]
        if saved_paths and current_paths and saved_paths == current_paths:
            if isinstance(saved_index, int) and 0 <= saved_index < len(self.output_records):
                return saved_index
        return 0

    def select_image_dirs(self):
        path = filedialog.askdirectory(title="이미지 폴더 선택")
        if path:
            current = self._parse_image_dirs()
            if path not in current:
                current.append(path)
            self._set_image_dirs(current)

    def select_json_paths(self):
        paths = filedialog.askopenfilenames(
            title="JSON 파일들 선택",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if paths:
            self._set_json_paths(list(paths))

    def _build_records_from_images(self):
        records = []
        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        seen_names = set()
        for image_dir in self.image_dirs:
            if not image_dir or not os.path.isdir(image_dir):
                continue

            for name in sorted(os.listdir(image_dir)):
                full_path = os.path.join(image_dir, name)
                if not os.path.isfile(full_path):
                    continue
                if os.path.splitext(name)[1].lower() not in valid_exts:
                    continue
                if name in seen_names:
                    continue
                seen_names.add(name)
                records.append({
                    "imagePath": name,
                    "latitude": None,
                    "longitude": None,
                    "timestamp": "",
                    "items": [],
                })
        return records

    def load_project(self):
        if not self.image_dir_var.get() or not self.json_path_var.get():
            messagebox.showwarning("경고", "이미지 폴더들과 JSON 파일 경로를 모두 지정하세요.")
            return

        image_dirs = self._parse_image_dirs()
        if not image_dirs:
            messagebox.showwarning("경고", "이미지 폴더를 하나 이상 지정하세요.")
            return
        self._set_image_dirs(image_dirs)
        json_paths = self._parse_json_paths()
        if not json_paths:
            messagebox.showwarning("경고", "JSON 파일 경로를 하나 이상 지정하세요.")
            return

        self._set_json_paths(json_paths)
        self.read_only_mode = len(self.json_paths) > 1

        if len(self.json_paths) == 1 and not os.path.exists(self.json_paths[0]):
            data = self._build_records_from_images()
            if not data:
                messagebox.showwarning("경고", "이미지 폴더에서 초기 JSON을 만들 수 있는 이미지 파일을 찾지 못했습니다.")
                return
            self.records = data
            self.output_records = self._prepare_output_records(data)
            if not self.save_output(silent=True):
                return
            messagebox.showinfo("안내", f"JSON 파일이 없어 새로 생성했습니다.\n{self.json_paths[0]}")
        else:
            loaded_lists = []
            for path in self.json_paths:
                if not os.path.exists(path):
                    messagebox.showerror("오류", f"JSON 파일을 찾을 수 없습니다.\n{path}")
                    return
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        data = json.load(file)
                except Exception as exc:
                    messagebox.showerror("오류", f"JSON 파일을 읽지 못했습니다.\n{path}\n\n{exc}")
                    return
                if not isinstance(data, list):
                    messagebox.showerror("오류", f"JSON 파일은 리스트 형태여야 합니다.\n{path}")
                    return
                loaded_lists.append(self._prepare_output_records(data))

            self.records = loaded_lists[0] if loaded_lists else []
            if len(loaded_lists) == 1:
                self.output_records = loaded_lists[0]
            else:
                self.output_records = self._merge_record_lists(loaded_lists)
                messagebox.showinfo("안내", f"{len(self.json_paths)}개의 JSON 파일을 병합해 읽기 전용으로 열었습니다.")

        if not self.output_records:
            messagebox.showinfo("안내", "불러올 데이터가 없습니다.")
            return

        self.current_index = self._get_initial_index()
        self.load_record(self.current_index)
        self.update_progress()

    def _prepare_output_records(self, data):
        prepared = []
        for item in data:
            source = deepcopy(item)
            items = source.get("items")
            normalized_items = []

            if isinstance(items, list):
                for entry in items:
                    if not isinstance(entry, dict):
                        continue
                    normalized_items.append({
                        "label": entry.get("label", ""),
                        "size": entry.get("size", ""),
                        "quantity": entry.get("quantity", 1),
                    })
            else:
                label = source.get("label")
                size = source.get("size")
                quantity = source.get("quantity", 1)
                if label and size:
                    normalized_items.append({
                        "label": label,
                        "size": size,
                        "quantity": quantity,
                    })

            prepared.append({
                "imagePath": source.get("imagePath", ""),
                "latitude": source.get("latitude"),
                "longitude": source.get("longitude"),
                "timestamp": source.get("timestamp", ""),
                "items": normalized_items,
            })
        return prepared

    def resolve_image_path(self, image_path):
        if not image_path:
            return None

        normalized = os.path.normpath(image_path)
        candidates = []

        if os.path.isabs(normalized):
            candidates.append(normalized)
        else:
            rel_path = image_path.lstrip("/\\").replace("/", os.sep)
            for image_dir in self.image_dirs:
                candidates.append(os.path.join(image_dir, rel_path))

        basename = os.path.basename(normalized)
        if basename:
            for image_dir in self.image_dirs:
                candidates.append(os.path.join(image_dir, basename))

        seen = set()
        for candidate in candidates:
            full = os.path.normpath(candidate)
            if full in seen:
                continue
            seen.add(full)
            if os.path.exists(full):
                return full
        return None

    def _extract_exif_metadata(self, image_path):
        try:
            with Image.open(image_path) as img:
                exif = img.getexif()
                result = {"latitude": None, "longitude": None, "timestamp": ""}
                if not exif:
                    return result

                gps_tag_id = None
                for tag_id, value in exif.items():
                    name = TAGS.get(tag_id, tag_id)
                    if name == "GPSInfo":
                        gps_tag_id = tag_id
                    elif name in {"DateTimeOriginal", "DateTime"} and not result["timestamp"]:
                        if isinstance(value, str):
                            result["timestamp"] = value.replace(":", "-", 2).replace(" ", "T")

                if gps_tag_id is not None:
                    gps_ifd = exif.get_ifd(gps_tag_id)
                    gps = {GPSTAGS.get(key, key): value for key, value in gps_ifd.items()}
                    lat = gps.get("GPSLatitude")
                    lat_ref = gps.get("GPSLatitudeRef")
                    lon = gps.get("GPSLongitude")
                    lon_ref = gps.get("GPSLongitudeRef")
                    if lat and lat_ref and lon and lon_ref:
                        result["latitude"] = _dms_to_decimal(lat, lat_ref)
                        result["longitude"] = _dms_to_decimal(lon, lon_ref)

                return result
        except Exception:
            return {"latitude": None, "longitude": None, "timestamp": ""}

    def _fill_metadata_from_exif(self):
        if not self.current_record:
            return

        needs_lat = self.current_record.get("latitude") in (None, "")
        needs_lon = self.current_record.get("longitude") in (None, "")
        needs_time = not self.current_record.get("timestamp")
        if not (needs_lat or needs_lon or needs_time):
            return

        path = self.resolve_image_path(self.current_record.get("imagePath", ""))
        if not path:
            return

        exif_meta = self._extract_exif_metadata(path)
        if needs_lat and exif_meta["latitude"] is not None:
            self.current_record["latitude"] = exif_meta["latitude"]
        if needs_lon and exif_meta["longitude"] is not None:
            self.current_record["longitude"] = exif_meta["longitude"]
        if needs_time and exif_meta["timestamp"]:
            self.current_record["timestamp"] = exif_meta["timestamp"]

    def load_record(self, index):
        if index < 0 or index >= len(self.output_records):
            return

        self.current_index = index
        self.current_record = self.output_records[index]
        self._fill_metadata_from_exif()
        self.selected_item_index = None
        self.item_listbox.selection_clear(0, tk.END)

        title = self.current_record.get("imagePath") or f"index {index}"
        self.record_title_var.set(f"{index + 1}/{len(self.output_records)} - {title}")
        self.render_metadata()
        self.load_image()
        self.refresh_item_list()
        self.update_progress()
        self._save_app_state()

    def render_metadata(self):
        record = self.current_record or {}
        lines = [
            f"imagePath: {record.get('imagePath', '')}",
            f"timestamp: {record.get('timestamp', '')}",
            f"latitude: {record.get('latitude', '')}",
            f"longitude: {record.get('longitude', '')}",
        ]
        self.meta_text.configure(state="normal")
        self.meta_text.delete("1.0", tk.END)
        self.meta_text.insert(tk.END, "\n".join(lines))
        self.meta_text.configure(state="disabled")

    def on_canvas_resize(self, event=None):
        if self.original_image is not None:
            self.load_image()

    def load_image(self):
        self.canvas.delete("all")
        path = self.resolve_image_path(self.current_record.get("imagePath", ""))
        canvas_w = max(self.canvas.winfo_width(), 1)
        canvas_h = max(self.canvas.winfo_height(), 1)

        if not path:
            self.original_image = None
            self.canvas.create_text(
                canvas_w // 2,
                canvas_h // 2,
                text="이미지를 찾을 수 없습니다.\nimagePath와 이미지 폴더를 확인하세요.",
                fill="white",
                font=("Arial", 18),
                justify="center",
            )
            return

        try:
            with Image.open(path) as source:
                self.original_image = source.convert("RGB")
        except Exception as exc:
            self.original_image = None
            self.canvas.create_text(
                canvas_w // 2,
                canvas_h // 2,
                text=f"이미지를 열 수 없습니다.\n{exc}",
                fill="white",
                font=("Arial", 18),
                justify="center",
            )
            return

        img_w, img_h = self.original_image.size
        scale = min(canvas_w / img_w, canvas_h / img_h)
        self.display_scale = scale
        self.display_w = max(int(img_w * scale), 1)
        self.display_h = max(int(img_h * scale), 1)
        self.display_offset_x = (canvas_w - self.display_w) // 2
        self.display_offset_y = (canvas_h - self.display_h) // 2

        resized = self.original_image.resize((self.display_w, self.display_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        self.canvas.create_image(self.display_offset_x, self.display_offset_y, anchor="nw", image=self.tk_image)

    def refresh_item_list(self):
        self.item_listbox.delete(0, tk.END)
        items = self.current_record.get("items", [])
        for idx, item in enumerate(items):
            text = f"{idx + 1}. {item.get('label', '')} / {item.get('size', '')} / quantity={item.get('quantity', 1)}"
            self.item_listbox.insert(tk.END, text)

        if self.selected_item_index is not None and 0 <= self.selected_item_index < len(items):
            self.item_listbox.selection_set(self.selected_item_index)
            self.item_listbox.see(self.selected_item_index)

    def on_select_item(self, event=None):
        selection = self.item_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        self.selected_item_index = idx
        item = self.current_record.get("items", [])[idx]
        self.label_var.set(item.get("label", LABELS[0]))
        self.size_var.set(item.get("size", SIZE_OPTIONS[0]))
        self.quantity_var.set(str(item.get("quantity", 1)))
        self.size_guide_var.set(SIZE_GUIDE[self.size_var.get()])

    def add_item(self):
        if not self._ensure_editable():
            return
        if not self.current_record:
            return
        quantity = self._validated_quantity()
        if quantity is None:
            return
        item = {
            "label": self.label_var.get(),
            "size": self.size_var.get(),
            "quantity": quantity,
        }
        self.current_record.setdefault("items", []).append(item)
        self.selected_item_index = len(self.current_record["items"]) - 1
        self.refresh_item_list()
        self.save_current_record(auto=True)

    def update_selected_item(self):
        if not self._ensure_editable():
            return
        if self.selected_item_index is None:
            messagebox.showinfo("안내", "먼저 목록에서 수정할 항목을 선택하세요.")
            return
        quantity = self._validated_quantity()
        if quantity is None:
            return
        items = self.current_record.get("items", [])
        if not (0 <= self.selected_item_index < len(items)):
            return
        items[self.selected_item_index] = {
            "label": self.label_var.get(),
            "size": self.size_var.get(),
            "quantity": quantity,
        }
        self.refresh_item_list()
        self.save_current_record(auto=True)

    def delete_selected_item(self):
        if not self._ensure_editable():
            return
        if self.selected_item_index is None:
            messagebox.showinfo("안내", "삭제할 항목을 선택하세요.")
            return
        items = self.current_record.get("items", [])
        if not (0 <= self.selected_item_index < len(items)):
            return
        del items[self.selected_item_index]
        self.selected_item_index = None
        self.refresh_item_list()
        self.save_current_record(auto=True)

    def clear_current_items(self):
        if not self._ensure_editable():
            return
        if not self.current_record:
            return
        self.current_record["items"] = []
        self.selected_item_index = None
        self.refresh_item_list()
        self.save_current_record(auto=True)
        messagebox.showinfo("안내", "현재 이미지의 쓰레기 항목을 초기화했습니다.")

    def save_current_record(self, auto=False):
        if self.read_only_mode:
            if not auto:
                messagebox.showinfo("안내", "여러 JSON 파일을 병합해 연 상태에서는 저장할 수 없습니다.")
            return True
        if self.current_index < 0 or self.current_index >= len(self.output_records):
            return True
        self.output_records[self.current_index] = self.current_record
        return self.save_output(silent=auto)

    def save_output(self, silent=False):
        if self.read_only_mode:
            if not silent:
                messagebox.showinfo("안내", "여러 JSON 파일을 병합해 연 상태에서는 저장할 수 없습니다.")
            return False
        if not self.json_path:
            if not silent:
                messagebox.showwarning("경고", "JSON 파일 경로를 먼저 지정하세요.")
            return False
        try:
            with open(self.json_path, "w", encoding="utf-8") as file:
                json.dump(self.output_records, file, ensure_ascii=False, indent=2)
            self._save_app_state()
            if not silent:
                messagebox.showinfo("저장 완료", f"JSON 저장 완료\n{self.json_path}")
            return True
        except Exception as exc:
            messagebox.showerror("오류", f"저장 실패\n{exc}")
            return False

    def prev_record(self):
        if self.current_index > 0 and self.save_current_record(auto=True):
            self.load_record(self.current_index - 1)

    def next_record(self):
        if self.current_index < len(self.output_records) - 1 and self.save_current_record(auto=True):
            self.load_record(self.current_index + 1)

    def save_and_next_record(self):
        if self.current_index < 0:
            return
        if self.save_current_record(auto=True):
            if self.current_index < len(self.output_records) - 1:
                self.load_record(self.current_index + 1)
            else:
                messagebox.showinfo("안내", "마지막 이미지입니다. 현재 결과만 저장했습니다.")

    def update_progress(self):
        if not self.output_records:
            self.progress_var.set("데이터를 불러오세요.")
            return
        done = sum(1 for record in self.output_records if record.get("items"))
        total = len(self.output_records)
        self.progress_var.set(f"진행률: {done}/{total} 항목에 items 존재")


if __name__ == "__main__":
    try:
        from PIL import Image, ImageTk  # noqa: F401
    except ImportError:
        raise SystemExit("Pillow가 필요합니다. 설치: pip install pillow")

    root = tk.Tk()
    app = PloggingLabelingTool(root)
    root.mainloop()
