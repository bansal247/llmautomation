import sqlite3
import json
from contextlib import contextmanager

DB_PATH = "products.db"


class ProductsDB:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.create_table()
        self.ensure_schema()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def connection(self):
        conn = self.get_connection()

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_table(self):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                sku INTEGER UNIQUE,

                title TEXT NOT NULL,
                subtitle TEXT,

                description_opening TEXT,
                description_bullets TEXT,

                meta_title TEXT,
                meta_description TEXT,
                alt_text TEXT,

                variants TEXT,
                product_type TEXT,
                product_tags TEXT,
                set_includes TEXT,

                price REAL,

                original_image_path TEXT,
                generated_image_path TEXT,

                ready_for_upload INTEGER DEFAULT 0,
                uploaded_to_shopify INTEGER DEFAULT 0,
                shopify_image_url TEXT UNIQUE,
                shopify_product_id TEXT UNIQUE,
                regenerate_image INTEGER DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

    def ensure_schema(self):
        """Safe migration for existing DBs"""
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(products)")
            columns = [row["name"] for row in cur.fetchall()]

            if "sku" not in columns:
                cur.execute("ALTER TABLE products ADD COLUMN sku INTEGER")

    def add_product(
        self,
        product,
        sku,
        original_image_path,
        generated_image_path
    ):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO products (
                sku,
                title,
                subtitle,
                description_opening,
                description_bullets,
                meta_title,
                meta_description,
                alt_text,
                variants,
                product_type,
                product_tags,
                set_includes,
                price,
                original_image_path,
                generated_image_path,
                ready_for_upload,
                uploaded_to_shopify,
                regenerate_image
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sku,
                product.get("title"),
                product.get("subtitle"),
                product.get("description", {}).get("opening"),
                json.dumps(product.get("description", {}).get("bullets", [])),
                product.get("meta_title"),
                product.get("meta_description"),
                product.get("alt_text"),
                json.dumps(product.get("variants", [])),
                product.get("product_type"),
                json.dumps(product.get("product_tags", [])),
                json.dumps(product.get("set_includes", [])),
                product.get("price"),
                original_image_path,
                generated_image_path,
                0,
                0,
                0
            ))
            product_id = cur.lastrowid
            return product_id

    def mark_for_regeneration(self, product_id, regenerate=True):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            UPDATE products
            SET regenerate_image = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (1 if regenerate else 0, product_id))

    def get_next_pending_product(self):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT *
            FROM products
            WHERE ready_for_upload = 0
            ORDER BY id
            LIMIT 1
            """)

            row = cur.fetchone()
            return self._row_to_product(row) if row else None
    
    def get_next_ready_for_upload_product(self):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT *
            FROM products
            WHERE ready_for_upload = 1
            AND uploaded_to_shopify = 0
            ORDER BY id
            LIMIT 1
            """)

            row = cur.fetchone()
            return self._row_to_product(row) if row else None

    def get_pending_products(self):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT *
            FROM products
            WHERE ready_for_upload = 0
            ORDER BY id
            """)

            rows = cur.fetchall()
            return [self._row_to_product(row) for row in rows]
        
    def get_regenerate_image_products(self):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT *
            FROM products
            WHERE regenerate_image = 1
            ORDER BY id
            """)

            rows = cur.fetchall()
            return [self._row_to_product(row) for row in rows]

    def get_product_by_shopify_image_url(self, shopify_image_url):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT *
            FROM products
            WHERE shopify_image_url = ?
            """, (shopify_image_url,))

            row = cur.fetchone()
            return self._row_to_product(row) if row else None

    def mark_uploaded(self, product_id, shopify_image_url, shopify_product_id):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            UPDATE products
            SET
                uploaded_to_shopify = 1,
                shopify_image_url = ?,
                shopify_product_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (
                shopify_image_url,
                shopify_product_id,
                product_id
            ))
    
    def update_product(self, product_id, updates):
        if not updates:
            return

        with self.connection() as conn:
            cur = conn.cursor()
            fields = []
            values = []

            json_fields = {
                "description_bullets",
                "variants",
                "product_tags",
                "set_includes"
            }

            for key, value in updates.items():
                if key in json_fields:
                    value = json.dumps(value)

                fields.append(f"{key} = ?")
                values.append(value)

            fields.append("updated_at = CURRENT_TIMESTAMP")

            sql = f"""
            UPDATE products
            SET {", ".join(fields)}
            WHERE id = ?
            """
            values.append(product_id)
            cur.execute(sql, values)

    def mark_ready_for_upload(self, product_id, ready_for_upload=True):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            UPDATE products
            SET ready_for_upload = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (1 if ready_for_upload else 0, product_id))

    def update_product_generated_image_path(self, product_id, path):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            UPDATE products
            SET generated_image_path = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (path, product_id))

    def delete_product(self, shopify_image_url):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            DELETE FROM products
            WHERE shopify_image_url = ?
            """, (shopify_image_url,))

            deleted = cur.rowcount > 0
            return deleted

    def _row_to_product(self, row):
        product = dict(row)

        product["description"] = {
            "opening": product.pop("description_opening"),
            "bullets": json.loads(product.pop("description_bullets") or "[]")
        }

        product["variants"] = json.loads(product["variants"] or "[]")
        product["product_tags"] = json.loads(product["product_tags"] or "[]")
        product["set_includes"] = json.loads(product["set_includes"] or "[]")

        return product

    def get_last_10_products(self):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT *
            FROM products
            ORDER BY COALESCE(updated_at, created_at) DESC
            LIMIT 10
            """)
            rows = cur.fetchall()
            return [self._row_to_product(row) for row in rows]