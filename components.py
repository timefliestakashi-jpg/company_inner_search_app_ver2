"""
このファイルは、画面表示に特化した関数定義のファイルです。
"""

############################################################
# ライブラリの読み込み
############################################################
import streamlit as st
import utils
import constants as ct
from typing import Optional
# NEW: 追加インポート
from pathlib import Path
import os

# NEW: データルート解決ヘルパー（env / secrets / constants を順に見る）
def _get_data_root() -> Path:
    candidates = []
    try:
        if "DATA_ROOT" in st.secrets:
            candidates.append(st.secrets["DATA_ROOT"])
    except Exception:
        pass
    if os.getenv("DATA_ROOT"):
        candidates.append(os.getenv("DATA_ROOT"))
    if hasattr(ct, "DATA_DIR"):
        candidates.append(getattr(ct, "DATA_DIR"))
    candidates.append(Path(__file__).resolve().parent / "data")  # デフォルト

    for c in candidates:
        try:
            return Path(c).resolve()
        except Exception:
            continue
    return Path(__file__).resolve().parent

# NEW: データルートを基準に、絶対パスを相対表示用に正規化（デプロイ先でも安定）
def _normalize_source_path(path: str) -> str:
    if not path:
        return ""
    s = str(path).replace("\\", "/")  # Windows区切り対策
    parts = [p for p in s.split("/") if p]

    # 1) どこかに "data" セグメントが含まれていれば、そこからの相対にする
    for i, part in enumerate(parts):
        if part.lower() == "data":
            tail = "/".join(parts[i:])
            return f"./{tail}"

    # 2) DATA_ROOT が分かるなら、その配下相対にする
    try:
        data_root = _get_data_root()
        rel = os.path.relpath(s, start=str(data_root))
        if not rel.startswith(".."):
            return f"./{rel}"
    except Exception:
        pass

    # 3) それでも無理ならファイル名のみ（環境依存の絶対パスは出さない）
    return os.path.basename(s)

def _format_file_info(path: str, page_number: Optional[int] = None) -> str:
    """
    ファイルパスを表示用に整形する。
    PDFでページ番号がある場合は「（ページNo.X）」を付与。
    """
    # NEW: 先にパスを正規化してから表示（デプロイ先でも ./data/... 表示）
    path = _normalize_source_path(path)
    if path.lower().endswith(".pdf") and page_number is not None:
        try:
            return f"{path}（ページNo.{int(page_number)+1}）"
        except Exception:
            return f"{path}（ページNo.{page_number}）"
    return path

############################################################
# 関数定義
############################################################

def _ensure_state():
    if "mode" not in st.session_state:
        st.session_state.mode = ct.ANSWER_MODE_1

# ===== メイン：タイトル＋初期メッセージ（挨拶/注意） =====
def display_app_title():
    """タイトルを中央寄せで表示"""
    st.markdown(
        f"""
        <h1 style="text-align:center; margin-top:0.5rem;">
            {ct.APP_NAME}
        </h1>
        """,
        unsafe_allow_html=True,
    )

def display_initial_ai_message():
    """メイン側：挨拶（緑）と注意（黄）だけを表示"""
    with st.chat_message("assistant"):
        st.success(
            "こんにちは。私は社内文書の情報をもとに回答する生成AIチャットボットです。"
            "サイドバーで利用目的を選択し、画面下部のチャット欄からメッセージを送信してください。"
        )
        st.warning("具体的に入力したほうが期待通りの回答を得やすいです。")

# ===== サイドバー：モード選択＋使い方ガイド =====
def display_sidebar():
    """左サイドバーにモード選択と説明ブロックを表示"""
    _ensure_state()
    with st.sidebar:
        st.markdown("### 利用目的")
        st.session_state.mode = st.radio(
            label="利用目的を選択",
            options=[ct.ANSWER_MODE_1, ct.ANSWER_MODE_2],
            index=[ct.ANSWER_MODE_1, ct.ANSWER_MODE_2].index(st.session_state.mode),
        )

        st.markdown("---")
        # 「社内文書検索」の説明
        st.markdown("**「社内文書検索」を選択した場合**")
        st.info("入力内容と関連性が高い社内文書のありかを検索できます。")
        st.code("【入力例】\n社員の育成方針に関するMTGの議事録", wrap_lines=True, language=None)

        st.markdown("")
        # 「社内問い合わせ」の説明
        st.markdown("**「社内問い合わせ」を選択した場合**")
        st.info("質問・要望に対して、社内文書の情報をもとに回答を得られます。")
        st.code("【入力例】\n人事部に所属している従業員情報を一覧化して", wrap_lines=True, language=None)

# ===== 使い方 =====
# ページ描画側では、以下の順で呼び出してください。
# display_sidebar()
# display_app_title()
# display_initial_ai_message()


def display_conversation_log():
    """
    会話ログの一覧表示
    """
    # 会話ログのループ処理
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(message["content"])
            else:
                if message["content"]["mode"] == ct.ANSWER_MODE_1:
                    if not "no_file_path_flg" in message["content"]:
                        st.markdown(message["content"]["main_message"])

                        icon = utils.get_source_icon(message['content']['main_file_path'])
                        # ここで PDF のみページ番号を付与して表示
                        main_path = message["content"]["main_file_path"]
                        main_page = message["content"].get("main_page_number")
                        st.success(_format_file_info(main_path, main_page), icon=icon)

                        if "sub_message" in message["content"]:
                            st.markdown(message["content"]["sub_message"])
                            for sub_choice in message["content"]["sub_choices"]:
                                icon = utils.get_source_icon(sub_choice['source'])
                                # ここで PDF のみページ番号を付与して表示
                                st.info(_format_file_info(sub_choice['source'], sub_choice.get("page_number")), icon=icon)
                    else:
                        st.markdown(message["content"]["answer"])
                else:
                    st.markdown(message["content"]["answer"])
                    if "file_info_list" in message["content"]:
                        st.divider()
                        st.markdown(f"##### {message['content']['message']}")
                        # file_info_list は display_contact_llm_response で整形済み文字列
                        for file_info in message["content"]["file_info_list"]:
                            icon = utils.get_source_icon(file_info)
                            st.info(file_info, icon=icon)

def display_search_llm_response(llm_response):
    """
    「社内文書検索」モードにおけるLLMレスポンスを表示
    """
    if llm_response["context"] and llm_response["answer"] != ct.NO_DOC_MATCH_ANSWER:
        main_file_path = llm_response["context"][0].metadata["source"]
        main_message = "入力内容に関する情報は、以下のファイルに含まれている可能性があります。"
        st.markdown(main_message)

        icon = utils.get_source_icon(main_file_path)
        # PDF ならページ番号を付けて表示
        main_page_number = llm_response["context"][0].metadata.get("page")
        st.success(_format_file_info(main_file_path, main_page_number), icon=icon)

        sub_choices = []
        duplicate_check_list = []

        for document in llm_response["context"][1:]:
            sub_file_path = document.metadata["source"]
            if sub_file_path == main_file_path:
                continue
            if sub_file_path in duplicate_check_list:
                continue
            duplicate_check_list.append(sub_file_path)

            if "page" in document.metadata:
                sub_page_number = document.metadata["page"]
                sub_choice = {"source": _normalize_source_path(sub_file_path), "page_number": sub_page_number}  # NEW: 正規化
            else:
                sub_choice = {"source": _normalize_source_path(sub_file_path)}  # NEW: 正規化
            sub_choices.append(sub_choice)

        if sub_choices:
            sub_message = "その他、ファイルありかの候補を提示します。"
            st.markdown(sub_message)
            for sub_choice in sub_choices:
                icon = utils.get_source_icon(sub_choice['source'])
                st.info(_format_file_info(sub_choice['source'], sub_choice.get("page_number")), icon=icon)

        content = {}
        content["mode"] = ct.ANSWER_MODE_1
        content["main_message"] = main_message
        content["main_file_path"] = _normalize_source_path(main_file_path)  # NEW: 正規化して保存
        if main_page_number is not None:
            content["main_page_number"] = main_page_number
        if sub_choices:
            content["sub_message"] = sub_message
            content["sub_choices"] = sub_choices
    else:
        st.markdown(ct.NO_DOC_MATCH_MESSAGE)
        content = {}
        content["mode"] = ct.ANSWER_MODE_1
        content["answer"] = ct.NO_DOC_MATCH_MESSAGE
        content["no_file_path_flg"] = True

    return content


def display_contact_llm_response(llm_response):
    """
    「社内問い合わせ」モードにおけるLLMレスポンスを表示
    """
    st.markdown(llm_response["answer"])

    if llm_response["answer"] != ct.INQUIRY_NO_MATCH_ANSWER:
        st.divider()
        message = "情報源"
        st.markdown(f"##### {message}")

        file_path_list = []
        file_info_list = []

        for document in llm_response["context"]:
            file_path = document.metadata["source"]
            if file_path in file_path_list:
                continue

            page_number = document.metadata.get("page")
            # NEW: 表示前にパスを正規化
            display_path = _normalize_source_path(file_path)
            file_info = _format_file_info(display_path, page_number)

            icon = utils.get_source_icon(file_path)
            st.info(file_info, icon=icon)

            file_path_list.append(file_path)
            file_info_list.append(file_info)

    content = {}
    content["mode"] = ct.ANSWER_MODE_2
    content["answer"] = llm_response["answer"]
    if llm_response["answer"] != ct.INQUIRY_NO_MATCH_ANSWER:
        content["message"] = message
        content["file_info_list"] = file_info_list

    return content