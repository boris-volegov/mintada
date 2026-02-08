import os


def iter_coin_html_targets(
    html_root: str,
    target_coin_type_id: int | None = None,
    target_coin_html_path: str | None = None,
):
    if target_coin_type_id is not None and target_coin_html_path:
        if os.path.isfile(target_coin_html_path):
            yield target_coin_type_id, target_coin_html_path
        else:
            print(
                f"[WARN] Target coin html path not found for coin_type_id={target_coin_type_id}: "
                f"{target_coin_html_path}"
            )
        return

    if not os.path.exists(html_root):
        print(f"HTML root folder not found at: {html_root}")
        return

    target_found = False
    issuer_folders = [f for f in os.listdir(html_root) if os.path.isdir(os.path.join(html_root, f))]

    for issuer_folder in issuer_folders:
        issuer_path = os.path.join(html_root, issuer_folder)
        coin_folders = [f for f in os.listdir(issuer_path) if os.path.isdir(os.path.join(issuer_path, f))]

        for coin_folder in coin_folders:
            try:
                coin_type_id = int(coin_folder.split("_")[-1])
            except ValueError:
                continue

            if target_coin_type_id is not None and coin_type_id != target_coin_type_id:
                continue

            coin_html_path = os.path.join(issuer_path, coin_folder, "coin_type.html")
            if not os.path.isfile(coin_html_path):
                continue

            yield coin_type_id, coin_html_path
            target_found = True

            if target_coin_type_id is not None:
                return

    if target_coin_type_id is not None and not target_found:
        print(f"[WARN] Could not find coin_type.html for target coin_type_id={target_coin_type_id}.")
