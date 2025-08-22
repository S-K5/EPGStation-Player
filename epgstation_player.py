import requests
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
from io import BytesIO
from datetime import datetime

# ----- 設定（メモリ上のみ） -----
config = {
    "epgstation_url": "http://192.168.0.177:8888",
    "potplayer_path": r"C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe",
    "limit": 500,
    "offset": 0,
}

selected_record = None
thumbnails = {}

# ----- フォント・カラー設定（Win11風） -----
default_font = ("HGSｺﾞｼｯｸE", 10)
title_font = ("HGSｺﾞｼｯｸE", 14)
button_font = ("BIZ UDゴシック", 11, "bold")
bg_color = "#F3F3F3"
panel_bg = "#FFFFFF"
accent_color = "#0A84FF"
text_color = "#111111"
hover_color = "#D0E7FF"

# ----- 設定画面 -----
def show_settings():
    settings_win = tk.Toplevel(root)
    settings_win.title("設定")
    settings_win.geometry("400x160")
    settings_win.resizable(False, False)
    settings_win.transient(root)
    settings_win.grab_set()
    settings_win.configure(bg=bg_color)

    main_frame = tk.Frame(settings_win, padx=15, pady=15, bg=bg_color)
    main_frame.pack(fill="both", expand=True)

    url_var = tk.StringVar(value=config.get("epgstation_url", ""))
    limit_var = tk.IntVar(value=config.get("limit", 500))
    main_frame.columnconfigure(1, weight=1)

    tk.Label(main_frame, text="EPGStation URL:", bg=bg_color, font=default_font).grid(row=0, column=0, sticky="w", pady=5)
    tk.Entry(main_frame, textvariable=url_var, font=default_font).grid(row=0, column=1, sticky="ew")
    tk.Label(main_frame, text="取得件数:", bg=bg_color, font=default_font).grid(row=1, column=0, sticky="w", pady=5)
    tk.Entry(main_frame, textvariable=limit_var, font=default_font).grid(row=1, column=1, sticky="ew")

    button_frame = tk.Frame(main_frame, bg=bg_color)
    button_frame.grid(row=2, column=0, columnspan=2, pady=15)

    def on_save():
        try:
            new_url = url_var.get().strip()
            if new_url and not (new_url.startswith("http://") or new_url.startswith("https://")):
                new_url = "http://" + new_url
            new_url = new_url.rstrip("/")
            new_limit = limit_var.get()
            if not new_url:
                messagebox.showerror("エラー", "EPGStation URLは必須です。", parent=settings_win)
                return
            config["epgstation_url"] = new_url
            config["limit"] = new_limit
            settings_win.destroy()
            fetch_programs()
        except tk.TclError:
            messagebox.showerror("入力エラー", "取得件数には数値を入力してください。", parent=settings_win)
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=settings_win)

    save_btn = tk.Button(button_frame, text="保存", command=on_save, width=10, bg=accent_color, fg="white", font=button_font, relief="flat")
    save_btn.pack(side="left", padx=10)
    cancel_btn = tk.Button(button_frame, text="キャンセル", command=settings_win.destroy, width=10, bg="#AAAAAA", fg="white", font=button_font, relief="flat")
    cancel_btn.pack(side="left", padx=10)

    settings_win.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2) - (settings_win.winfo_width() // 2)
    y = root.winfo_y() + (root.winfo_height() // 2) - (settings_win.winfo_height() // 2)
    settings_win.geometry(f"+{x}+{y}")
    settings_win.wait_window()

# ----- 再生 -----
def play_selected():
    global selected_record
    record = selected_record
    if not isinstance(record, dict):
        messagebox.showerror("再生エラー", "正しい番組が選択されていません")
        return
    video_files = record.get("videoFiles", [])
    if not video_files:
        messagebox.showerror("再生エラー", "再生可能な動画ファイルがありません")
        return
    ts_file = next((vf for vf in video_files if vf.get("name")=="TS"), video_files[0])
    video_id = ts_file["id"]
    stream_url = f"{config['epgstation_url']}/api/videos/{video_id}/playlist"
    try:
        subprocess.Popen([config["potplayer_path"], stream_url])
    except Exception as e:
        messagebox.showerror("再生エラー", str(e))

# ----- 番組取得 -----
def fetch_programs():
    global selected_record
    for w in list_frame.winfo_children():
        w.destroy()
    thumbnails.clear()
    selected_record = None
    detail_thumb_label.config(image="")
    title_label.config(text="")
    time_label.config(text="")
    desc_label.config(text="")
    canvas_detail.yview_moveto(0)

    try:
        url = f"{config['epgstation_url']}/api/recorded"
        params = {"isHalfWidth":"true", "offset":config["offset"], "limit":config["limit"], "hasOriginalFile":"true"}
        res = requests.get(url, params=params, headers={"accept":"application/json"}, timeout=5)
        res.raise_for_status()
        records = res.json().get("records", [])

        for rec in records:
            frame = tk.Frame(list_frame, bd=1, relief="solid", bg=panel_bg, highlightbackground="#E0E0E0", highlightthickness=1)
            frame.pack(fill="x", pady=3, padx=3)

            # サムネイル
            thumb_id = rec.get("thumbnails",[None])[0]
            img_label = tk.Label(frame, bg=panel_bg)
            img_label.pack(side="left", padx=5, pady=5)
            if thumb_id:
                try:
                    thumb_url = f"{config['epgstation_url']}/api/thumbnails/{thumb_id}"
                    r = requests.get(thumb_url, headers={"accept":"image/jpeg"}, timeout=3)
                    img = Image.open(BytesIO(r.content)).resize((120,68))
                    photo = ImageTk.PhotoImage(img)
                    img_label.config(image=photo)
                    img_label.image = photo
                    thumbnails[rec["id"]] = photo
                except: pass

            # 放送時間
            start_ts = rec.get("startAt",0)//1000
            end_ts = rec.get("endAt",0)//1000
            start = datetime.fromtimestamp(start_ts)
            end = datetime.fromtimestamp(end_ts)
            dur = end - start
            h,m = divmod(dur.seconds//60,60)
            length_text = f"({h}h{m}m)" if h>0 else f"({m}m)"
            time_text = f"{start.strftime('%Y/%m/%d')} {start.strftime('%H:%M')}-{end.strftime('%H:%M')} {length_text}"

            # タイトル＋時間フレーム
            text_frame = tk.Frame(frame, bg=panel_bg)
            text_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

            title_lbl = tk.Label(text_frame, text=rec.get("name","unknown"),
                                justify="left",
                                anchor="w",
                                bg=panel_bg,
                                fg=text_color,
                                font=("BIZ UDゴシック", 10, "bold"),
                                wraplength=400)
            title_lbl.pack(side="top", anchor="w")

            time_lbl = tk.Label(text_frame, text=time_text,
                                justify="left",
                                anchor="w",
                                bg=panel_bg,
                                fg=text_color,
                                font=("HGSｺﾞｼｯｸE", 10))
            time_lbl.pack(side="top", anchor="w")

            # クリック時の動作
            def on_click(event, r=rec, fr=frame):
                global selected_record
                selected_record = r
                for w in list_frame.winfo_children():
                    w.config(bg=panel_bg)
                fr.config(bg=hover_color)

                # 詳細サムネイル更新
                thumb_id = r.get("thumbnails",[None])[0]
                if thumb_id:
                    try:
                        thumb_url = f"{config['epgstation_url']}/api/thumbnails/{thumb_id}"
                        resp = requests.get(thumb_url, headers={"accept":"image/jpeg"}, timeout=3)
                        img = Image.open(BytesIO(resp.content))
                        panel_width = scroll_content.winfo_width() or 350
                        w,h = img.size
                        ratio = panel_width / w
                        new_h = int(h * ratio)
                        img_resized = img.resize((panel_width,new_h))
                        photo_resized = ImageTk.PhotoImage(img_resized)
                        detail_thumb_label.config(image=photo_resized)
                        detail_thumb_label.image = photo_resized
                        detail_thumb_label.pack_configure(pady=(0,0))
                    except:
                        detail_thumb_label.config(image="")
                else:
                    detail_thumb_label.config(image="")

                # 番組名・放送時間
                title_label.config(text=r.get("name",""), font=title_font, fg=text_color)

                start_ts = r.get("startAt",0)//1000
                end_ts = r.get("endAt",0)//1000
                start = datetime.fromtimestamp(start_ts)
                end = datetime.fromtimestamp(end_ts)
                dur = end - start
                h,m = divmod(dur.seconds//60,60)
                length_text = f"({h}h{m}m)" if h>0 else f"({m}m)"
                detail_time_text = f"{start.strftime('%Y/%m/%d')} {start.strftime('%H:%M')}-{end.strftime('%H:%M')} {length_text}"
                time_label.config(text=detail_time_text, font=default_font, fg=text_color)

                # 詳細説明
                details = r.get("description","")
                ext = r.get("extended","")
                if isinstance(ext, dict):
                    for k,v in ext.items():
                        details += f"\n{k}:\n{v}"
                else:
                    details += f"\n{str(ext)}"
                desc_label.config(text=details, font=default_font, fg=text_color)
                canvas_detail.yview_moveto(0)

            # フレームと子にバインド（余白もクリック可能）
            for widget in (frame, img_label, text_frame, title_lbl, time_lbl):
                widget.bind("<Button-1>", on_click)

    except Exception as e:
        messagebox.showerror("取得エラー", f"番組情報の取得に失敗しました\n{e}")

# ----- GUI -----
root = tk.Tk()
root.title("EPGStation Player")
root.geometry("1000x640")
root.resizable(False, False)
root.configure(bg=bg_color)

header_frame = tk.Frame(root, bg=bg_color)
header_frame.pack(fill="x", padx=10, pady=(5,0))
top_frame = tk.Frame(root, bg=bg_color)
top_frame.pack(fill="both", expand=True, padx=5, pady=5)
bottom_frame = tk.Frame(root, bg=bg_color)
bottom_frame.pack(fill="x", padx=5, pady=(0,10))

settings_btn = tk.Button(header_frame, text="設定", command=show_settings, width=8, bg=accent_color, fg="white", font=button_font, relief="flat")
settings_btn.pack(side="right")

# 左：番組一覧
left_frame = tk.Frame(top_frame, width=600, bg=bg_color)
left_frame.pack(side="left", fill="y")
left_frame.pack_propagate(False)
canvas_list = tk.Canvas(left_frame, highlightthickness=0, bg=bg_color)
scrollbar_list = tk.Scrollbar(left_frame, orient="vertical", command=canvas_list.yview)
list_frame = tk.Frame(canvas_list, bg=bg_color)
canvas_list.create_window((0,0), window=list_frame, anchor="nw", tags="list_frame_window")
def configure_list_frame(event):
    canvas_list.itemconfig("list_frame_window", width=event.width)
canvas_list.bind("<Configure>", configure_list_frame)
list_frame.bind("<Configure>", lambda e: canvas_list.configure(scrollregion=canvas_list.bbox("all")))
canvas_list.configure(yscrollcommand=scrollbar_list.set)
canvas_list.pack(side="left", fill="both", expand=True)
scrollbar_list.pack(side="right", fill="y")

# 右：詳細パネル
detail_frame = tk.Frame(top_frame, bd=1, relief="flat", bg=panel_bg)
detail_frame.pack(side="right", fill="both", expand=True, padx=(5,0))
canvas_detail = tk.Canvas(detail_frame, highlightthickness=0, bg=panel_bg)
scrollbar_detail = tk.Scrollbar(detail_frame, orient="vertical", command=canvas_detail.yview)
scroll_content = tk.Frame(canvas_detail, bg=panel_bg)
scroll_content.bind("<Configure>", lambda e: canvas_detail.configure(scrollregion=canvas_detail.bbox("all")))
canvas_detail.create_window((0,0), window=scroll_content, anchor="nw", tags="detail_content_window")
def configure_detail_content(event):
    canvas_detail.itemconfig("detail_content_window", width=event.width)
canvas_detail.bind("<Configure>", configure_detail_content)
canvas_detail.configure(yscrollcommand=scrollbar_detail.set)
canvas_detail.pack(side="left", fill="both", expand=True)
scrollbar_detail.pack(side="right", fill="y")

def _on_mousewheel(event):
    x,y = root.winfo_pointerxy()
    widget = root.winfo_containing(x,y)
    while widget:
        if widget == canvas_list:
            canvas_list.yview_scroll(int(-1*(event.delta/120)),"units")
            return
        if widget == canvas_detail:
            canvas_detail.yview_scroll(int(-1*(event.delta/120)),"units")
            return
        try:
            widget = widget.master
        except:
            return
root.bind_all("<MouseWheel>", _on_mousewheel)

# 詳細サムネイル
detail_thumb_label = tk.Label(scroll_content, bg=panel_bg)
detail_thumb_label.pack(pady=10)

title_label = tk.Label(scroll_content, text="", font=title_font, wraplength=350, justify="left", bg=panel_bg)
title_label.pack(pady=(5,2), padx=10, anchor='w')
time_label = tk.Label(scroll_content, text="", font=default_font, bg=panel_bg)
time_label.pack(pady=(0,2), padx=10, anchor='w')
desc_label = tk.Label(scroll_content, text="",
                      wraplength=350,
                      justify="left",
                      font=("HGSｺﾞｼｯｸE", 10, "normal"),
                      bg=panel_bg,
                      fg=text_color)
desc_label.pack(pady=(0,5), padx=10, anchor='w')

play_btn = tk.Button(bottom_frame, text="再生", command=play_selected, bg=accent_color, fg="white", font=button_font, relief="flat")
play_btn.pack(pady=5)

fetch_programs()
root.mainloop()
