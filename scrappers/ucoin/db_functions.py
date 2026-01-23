import sqlite3
from helper_functions import _extract_data_from_coin_image_link

def db_upsert_country(db_cursor, name: str, url_slug: str, url: str) -> int:
    db_cursor.execute("INSERT OR IGNORE INTO countries(name, url_slug, url) VALUES (?, ?, ?)", (name, url_slug, url))
    db_cursor.execute("SELECT rowid FROM countries WHERE url = ?", (url,))
    return db_cursor.fetchone()[0]

def db_get_country_id(db_cursor, country_url_slug):
    db_cursor.execute("SELECT id FROM countries WHERE url_slug = ?", (country_url_slug,))

    return db_cursor.fetchone()[0]

def db_get_coin_type_url(db_cursor, tid):
    db_cursor.execute("SELECT url FROM coin_types WHERE id = ?", (tid,))

    return db_cursor.fetchone()[0]

def db_get_coin_images(db_cursor, tid):
    db_cursor.execute("SELECT id, file_name, url_prefix, year FROM coin_images WHERE coin_type_id = ?", (tid,))

    # get column names from cursor.description
    orig_columns = [col[0] for col in db_cursor.description]
    columns = ["coin_instance_id" if c == "id" else c for c in orig_columns]

    rows = db_cursor.fetchall()

    # convert each tuple to a dict
    return [dict(zip(columns, row)) for row in rows]

def db_coin_type_exists(db_cursor, tid):
    db_cursor.execute("SELECT 1 FROM coin_types WHERE id = ? LIMIT 1", (tid,))
    return db_cursor.fetchone()

def db_delete_coin_type(db_connection, db_cursor, tid):
    db_cursor.execute("DELETE FROM coin_types WHERE id = ?", (tid,))
    
    db_connection.commit()


def db_upsert_country_rels(db_connection, db_cursor, child_country_slug, parent_country_slug):
    """
    Insert (child, parent) into country_rels using slugs, case-insensitive.
    Returns True if inserted, False if it already existed or either slug not found.
    """
    db_cursor.execute("""
        WITH
          c AS (SELECT id AS cid FROM countries WHERE url_slug = ? COLLATE NOCASE),
          p AS (SELECT id AS pid FROM countries WHERE url_slug = ? COLLATE NOCASE)
        INSERT INTO country_rels (child_country_id, parent_country_id)
        SELECT cid, pid
        FROM c, p
        WHERE cid IS NOT NULL
          AND pid IS NOT NULL
          AND cid <> pid
        ON CONFLICT(child_country_id, parent_country_id) DO NOTHING;
    """, (child_country_slug, parent_country_slug))
    
    db_connection.commit()

def db_upsert_exception(db_connection, db_cursor, coin_type_country_url_slug, country_url_slug, coin_type_url, exception_type):
    db_cursor.execute("""
        INSERT INTO coin_type_exceptions(coin_type_country_url_slug, country_url_slug, coin_type_url, exception_type)
        VALUES (?, ?, ?, ?)
    """, (coin_type_country_url_slug, country_url_slug, coin_type_url, exception_type))
    
    db_connection.commit()

def db_get_or_create_period_id(db_cursor, description: str, country_id: int) -> int:
    db_cursor.execute("""
        INSERT INTO coinage_periods(description, country_id)
        VALUES (?, ?)
        ON CONFLICT(description, country_id)
        DO UPDATE SET description = excluded.description
        RETURNING id
    """, (description, country_id))
    return db_cursor.fetchone()[0]

def db_get_or_create_theme_id(db_cursor, theme: str) -> int:
    db_cursor.execute("""
        INSERT INTO design_themes (description)
        VALUES (?)
        ON CONFLICT(description)
        DO UPDATE SET description = excluded.description
        RETURNING id
    """, (theme,))
    return db_cursor.fetchone()[0]

def db_get_or_create_description_id(db_cursor, description_text: str, description_key: str) -> int:
    db_cursor.execute("""
        INSERT INTO design_descriptions (text, key)
        VALUES (?, ?)
        ON CONFLICT(text, key)
        DO UPDATE SET text = excluded.text
        RETURNING id
    """, (description_text, description_key))
    return db_cursor.fetchone()[0]


def populate_coin_type_themes(db_cursor, tid, themes, is_obverse):
    if themes is not None and len(themes) > 0:
        for theme in themes:
            theme_id = db_get_or_create_theme_id(db_cursor, theme)

            db_cursor.execute(
                f"""INSERT INTO coin_type_themes (coin_type_id, theme_id, is_obverse)
                    VALUES (?, ?, ?)""",
                (tid, theme_id, is_obverse),
            )

def populate_coin_type_legends(db_cursor, tid, legends, is_obverse):
    if legends is not None and len(legends) > 0:
        for legend in legends:

            db_cursor.execute(
                f"""INSERT INTO coin_type_legends (coin_type_id, legend, is_obverse)
                    VALUES (?, ?, ?)""",
                (tid, legend, is_obverse),
            )            
            
def populate_coin_type_description(db_cursor, tid, face_info, is_obverse):
    if "description_text" in face_info and face_info["description_text"] is not None:
        description_key = face_info["description_key"]  if "description_key" in face_info else None
        description_id = db_get_or_create_description_id(db_cursor, face_info["description_text"], description_key)

        db_cursor.execute(
            f"""INSERT INTO coin_type_descriptions (coin_type_id, description_id, is_obverse)
                VALUES (?, ?, ?)""",
            (tid, description_id, is_obverse),
        )    

def populate_coin_type_designers(db_cursor, tid, obverse_creators, revers_creators):
    if obverse_creators is not None or revers_creators is not None:   
        db_cursor.execute(
            f"""UPDATE coin_types SET obverse_designer = ?, reverse_designer = ? WHERE id = ?""",
            (obverse_creators, revers_creators, tid),
        )    

def populate_coin_type_mintage_rows(db_connection, coin_type_id: int, rows: list[dict]):
    """
    Insert multiple mintage rows for a given coin_type_id.
    `rows` is a list of dicts with keys: year, unc, bu, proof, mint, mark.
    """
    sql = """
        INSERT INTO coin_type_mintage
        (coin_type_id, year, unc, bu, proof, mint, mark)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """

    # Build parameter tuples. Any missing key defaults to None/empty string.
    params = [
        (
            coin_type_id,
            row.get("year"),
            row.get("unc"),
            row.get("bu"),
            row.get("proof"),
            row.get("mint") or None,  # store NULL instead of empty string
            row.get("mark") or None,
        )
        for row in rows
    ]

    with db_connection:  # auto-commit on success / rollback on error
        db_connection.executemany(sql, params)    

def populate_coin_type(db_connection, db_cursor, tid, issue_type, country_id, url, coin_type_info, obverse_info, reverse_info, mintage_info):
    if "period" in coin_type_info and coin_type_info["period"] is not None:
        period_id = db_get_or_create_period_id(db_cursor, coin_type_info["period"], country_id)

        coin_type_info["period_id"] = period_id

        coin_instance_id, file_name, side, url_prefix = _extract_data_from_coin_image_link(obverse_info["reference_image_url"])
        coin_type_info["reference_coin_instance_id"] = coin_instance_id

    cols = [k for k, v in coin_type_info.items() if v is not None and k not in ("id", "country_id", "url", "country", "period", "currency")]

    if cols:
        placeholders = ", ".join("?" for _ in cols)
        collist = ", ".join(cols)
        values = [coin_type_info[c] for c in cols]

        db_cursor.execute(
            f"""INSERT INTO coin_types (id, issue_type, country_id, url, {collist})
                VALUES (?, ?, ?, ?, {placeholders})""",
            (tid, issue_type, country_id, url, *values),
        )

    populate_coin_type_themes(db_cursor, tid, obverse_info["themes"], True)
    populate_coin_type_themes(db_cursor, tid, reverse_info["themes"], False)

    populate_coin_type_description(db_cursor, tid, obverse_info, True)
    populate_coin_type_description(db_cursor, tid, reverse_info, False)

    populate_coin_type_legends(db_cursor, tid, obverse_info["legends"], True)
    populate_coin_type_legends(db_cursor, tid, reverse_info["legends"], False)

    populate_coin_type_designers(db_cursor, tid, obverse_info["creators"], reverse_info["creators"])

    populate_coin_type_mintage_rows(db_connection, tid, mintage_info)

    db_connection.commit()
    return

def populate_coin_images(db_connection, db_cursor, coin_type_id: int, coin_images: list[dict]):
    """
    Insert rows into coin_images.
    coin_gallery is a list of dicts like:
    {
        "coin_instance_id": "22828667",
        "file_name": "...",
        "url_prefix": "...",
        "year": 1974
    }
    """

    sql = """
        INSERT INTO coin_images
            (id, coin_type_id, file_name, url_prefix, year)
        VALUES (?, ?, ?, ?, ?)
    """
    
    params = []
    for coin_image in coin_images:
        params.append((
            int(coin_image["coin_instance_id"]),  # cast to int if your PK is INTEGER
            coin_type_id,
            coin_image.get("file_name"),
            coin_image.get("url_prefix"),
            coin_image.get("year")
        ))

    with db_connection:  # ensures commit/rollback
        db_cursor.executemany(sql, params)