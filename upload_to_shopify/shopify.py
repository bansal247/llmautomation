import json
import itertools
import mimetypes
import os
import requests
from typing import Optional
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(),"upload_to_shopify",".env"))

# Load environment variables
SHOP = os.getenv("SHOP")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
GRANT_TYPE = os.getenv("GRANT_TYPE")
API_VERSION = os.getenv("API_VERSION")


class ShopifyUploader:
    def __init__(self, db):
        auth_url = (
            f"https://{SHOP}/admin/oauth/access_token"
            f"?client_id={CLIENT_ID}"
            f"&grant_type={GRANT_TYPE}"
            f"&client_secret={CLIENT_SECRET}"
        )
        response = requests.post(auth_url)
        response.raise_for_status()
        print(f"Authenticated with Shopify at {datetime.now()}")
        self.url = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"
        # REST_URL = f"https://{SHOP}/admin/api/{API_VERSION}/products.json"
        self.headers = {
            "X-Shopify-Access-Token": response.json()['access_token'],
            "Content-Type": "application/json"
        }

        self.collections_data = self._fetch_all_collections()
        print(f"Fetched {len(self.collections_data['data']['collections']['edges'])} collections from Shopify at {datetime.now()}")

        self.publication_ids = self._fetch_all_publications()
        print(f"fetched publications : {self.publication_ids}")

    def upload_product(self, product_data):
        try:
            required_des = product_data['description']['opening'] + "<br><ul>" + "".join(f"<li>{b}</li>" for b in product_data['description']['bullets']) + "</ul>"
        except:
            print("Error constructing description HTML, falling back to plain text")
            return
        product_data["product_tags"].append("new-arrivals")
        if product_data["price"] <= 999:
            product_data["product_tags"].append("under-999")
        collection_ids = []
        for edge in self.collections_data['data']['collections']['edges']:
            if edge['node']['title'] == product_data["product_type"]:
                collection_ids.append(edge['node']['id'])
            if edge['node']['title'] in product_data["product_tags"]:
                collection_ids.append(edge['node']['id'])
        if not collection_ids:
            print(f"Collection '{product_data['product_type']}' not found for product '{product_data['title']}'")
            return
        
        # if len(product_data["variants"]) == 0:
        #     print("no variants for product:", product_data)
        #     return
        
        required_variants = []
        sku_counter = 0
        for v in product_data["variants"]:
            for value in v["values"]:
                required_variants.append({
                    "option_name": v["type"],
                    "option_value": value,
                    "sku": product_data["sku"] + sku_counter,
                    "price": str(product_data["price"]),
                })
                sku_counter += 1

        return self._create_shopify_product(
                sku=str(product_data["sku"]),
                title=product_data["title"],
                subtitle=product_data["subtitle"],
                meta_title=product_data["meta_title"],
                meta_description=product_data["meta_description"],
                product_type=product_data["product_type"],
                product_tags=product_data["product_tags"],
                set_includes=product_data["set_includes"],
                price=product_data["price"],
                description=required_des,
                image_path=product_data["generated_image_path"],
                variants=required_variants,
                collection_ids=collection_ids,
                publication_ids=self.publication_ids,
        )

    def shopify_graphql(self, query, variables=None):
        r = requests.post(self.url, json={"query": query, "variables": variables}, headers=self.headers)
        r.raise_for_status()
        return r.json()

    def fetch_metafields(self):
        query = """
        query MetafieldDefinitions($ownerType: MetafieldOwnerType!, $first: Int) {
        metafieldDefinitions(ownerType: $ownerType, first: $first) {
            nodes {
            name
            namespace
            key
            type {
                name
            }
            }
        }
        }
        """

        variables = {
            "ownerType": "PRODUCT",
            "first": 20
        }

        return self.shopify_graphql(query, variables)

    def _fetch_all_collections(self):
        query = """
                query {
                    collections(first: 100, query: "title:*") {
                        edges {
                        node {
                            id
                            title
                            handle
                            updatedAt
                        }
                        }
                    }
                }
                """
        return self.shopify_graphql(query)
    
    def _fetch_all_publications(self):
        publications_response = self.shopify_graphql("""query { publications(first: 10) { nodes { id name } } }""")
        publications_response["data"]["publications"]["nodes"]
        publication_ids = [pub['id'] for pub in publications_response["data"]["publications"]["nodes"]]
        return publication_ids

    def _create_shopify_product(
        self,
        sku: str,
        title: str,
        subtitle: str,
        meta_title: str,
        meta_description: str,
        product_type: str,
        product_tags: list[str],
        set_includes: list[str],
        price: str,
        description: str,
        image_path: str,
        variants: Optional[list[dict]] = None,
        collection_ids: Optional[list[str]] = None,
        location_id: Optional[str] = "gid://shopify/Location/81822777483",
        category_id: Optional[str] = "gid://shopify/TaxonomyCategory/aa-6",
        publication_ids: Optional[list[str]] = None,
    ) -> dict:
        """
        Create a product in Shopify via the Admin GraphQL API.
        Uploads image from a local file path via Shopify staged uploads.
        Inventory is untracked (CONTINUE / tracked=False) on all variants.
        """

        # 1. Upload local image via staged uploads
        shopify_image_url = self._upload_image(image_path, title)

        # 2. Build product options (for variant products)
        product_options = []
        if variants:
            option_map: dict[str, list[str]] = {}
            for v in variants:
                name = v.get("option_name", "Title")
                value = v.get("option_value", "Default")
                option_map.setdefault(name, [])
                if value not in option_map[name]:
                    option_map[name].append(value)

            product_options = [
                {"name": name, "values": [{"name": val} for val in values]}
                for name, values in option_map.items()
            ]

        # 3. Execute productCreate
        
        product_response = self.shopify_graphql(
            """
            mutation productCreate($product: ProductCreateInput!, $media: [CreateMediaInput!]) {
            productCreate(product: $product, media: $media) {
                product {
                id title handle status
                category { id name }
                options { id name position optionValues { id name } }
                variants(first: 50) {
                    edges { node { id title price inventoryItem { id sku } selectedOptions { name value } } }
                }
                seo { title description }
                metafields(first: 10) { edges { node { namespace key value } } }
                }
                userErrors { field message }
            }
            }
            """,
            {
                "product": {
                    "title": title,
                    "descriptionHtml": description,
                    "productType": product_type,
                    "tags": product_tags,
                    "seo": {"title": meta_title, "description": meta_description},
                    "metafields": [
                        {"namespace": "custom", "key": "subtitle", "value": subtitle, "type": "single_line_text_field"},
                        {"namespace": "custom", "key": "set_includes", "value": json.dumps(set_includes), "type": "list.single_line_text_field"},
                        {
                            "namespace": "custom",
                            "key": "return_policy",
                            "type": "rich_text_field",
                            "value": json.dumps({
                                "type": "root",
                                "children": [
                                    {
                                        "type": "paragraph",
                                        "children": [
                                            {"type": "text", "value": "See "},
                                            {
                                                "type": "link",
                                                "url": "https://www.piyagujwells.in/policies/refund-policy",
                                                "children": [{"type": "text", "value": "Return & Refund Policy"}]
                                            }
                                        ]
                                    }
                                ]
                            })
                        }
                    ],
                    **({"category": category_id} if category_id else {}),
                    **({"productOptions": product_options} if variants else {}),
                    **({"collectionsToJoin": collection_ids} if collection_ids else {}),
                },
                "media": [{"originalSource": shopify_image_url, "mediaContentType": "IMAGE", "alt": title}],
            },
        )

        if product_response.get("data", {}).get("productCreate", {}).get("userErrors"):
            return {"product_upload_response": product_response}

        product = product_response["data"]["productCreate"]["product"]

        # 4. Create missing variant combinations
        variant_create_response = None
        if variants:
            variant_create_response = self._create_missing_variants(product, variants, price, sku)

        # 5. Patch SKU / price / inventory policy on all variants
        variant_patch_response = self._patch_variants(product, variants, price, sku)

        # 6. Publish to channels
        publish_response = None
        if publication_ids:
            publish_response = self._publish_to_channels(product["id"], publication_ids)

        return {
            "product_upload_response": product_response,
            "variant_create_response": variant_create_response,
            "variant_patch_response": variant_patch_response,
            "publish_response": publish_response,
            "shopify_image_url":shopify_image_url,
        }

    def _upload_image(self, image_path: str, alt: str) -> str:
        """
        Uploads a local image to Shopify using the stagedUploadsCreate mutation.

        Steps:
        1. Ask Shopify for a pre-signed S3 upload URL (stagedUploadsCreate)
        2. HTTP PUT the file bytes to that URL with the required form fields
        3. Return the resourceUrl — Shopify uses this as the final CDN URL

        Args:
            image_path: Absolute or relative path to the local image file
            alt:        Alt text / product title (not used in upload, just for clarity)

        Returns:
            resourceUrl string to pass as originalSource in CreateMediaInput
        """
        filename  = os.path.basename(image_path)
        mime_type = mimetypes.guess_type(filename)[0] or "image/jpeg"
        file_size = str(os.path.getsize(image_path))

        # Step 1: get staged upload target from Shopify
        staged_response = self.shopify_graphql(
            """
            mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
            stagedUploadsCreate(input: $input) {
                stagedTargets {
                url
                resourceUrl
                parameters { name value }
                }
                userErrors { field message }
            }
            }
            """,
            {
                "input": [{
                    "filename":    filename,
                    "mimeType":    mime_type,
                    "fileSize":    file_size,
                    "httpMethod":  "PUT",
                    "resource":    "IMAGE",
                }]
            },
        )

        target = staged_response["data"]["stagedUploadsCreate"]["stagedTargets"][0]
        upload_url   = target["url"]
        resource_url = target["resourceUrl"]
        parameters   = {p["name"]: p["value"] for p in target["parameters"]}

        # Step 2: PUT the file to the pre-signed URL
        with open(image_path, "rb") as f:
            file_bytes = f.read()

        put_response = requests.put(
            upload_url,
            data=file_bytes,
            headers={
                "Content-Type":   mime_type,
                "Content-Length": file_size,
                **parameters,       # include any signed headers Shopify requires
            },
        )
        put_response.raise_for_status()

        # Step 3: return the CDN resource URL for use in productCreate media
        return resource_url

    def _create_missing_variants(self, product, variants, default_price, default_sku):
        """productCreate only creates the first combination. This creates the rest."""
        option_groups: dict[str, list[dict]] = {}
        for v in variants:
            name = v.get("option_name")
            if name:
                option_groups.setdefault(name, [])
                if not any(x["option_value"] == v["option_value"] for x in option_groups[name]):
                    option_groups[name].append(v)

        existing_titles = {edge["node"]["title"] for edge in product["variants"]["edges"]}
        option_id_map = {opt["name"]: opt["id"] for opt in product["options"]}

        variants_to_create = [
            {
                "optionValues": [
                    {"optionId": option_id_map[v["option_name"]], "name": v["option_value"]}
                    for v in combo
                ],
                "price": str(next((v.get("price") for v in combo if v.get("price")), default_price)),
                "inventoryItem": {
                    "sku": str(next((v.get("sku") for v in combo if v.get("sku")), default_sku)),
                    "tracked": False,
                },
                "inventoryPolicy": "CONTINUE",
            }
            for combo in itertools.product(*option_groups.values())
            if " / ".join(v["option_value"] for v in combo) not in existing_titles
        ]

        if not variants_to_create:
            return {}

        return self.shopify_graphql(
            """
            mutation productVariantsBulkCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
            productVariantsBulkCreate(productId: $productId, variants: $variants) {
                productVariants { id title price inventoryItem { id sku tracked } inventoryPolicy }
                userErrors { field message }
            }
            }
            """,
            {"productId": product["id"], "variants": variants_to_create},
        )

    def _fetch_all_variants(self, product_id: str) -> list[dict]:
        query = """
        query getVariants($productId: ID!, $cursor: String) {
        product(id: $productId) {
            variants(first: 100, after: $cursor) {
            pageInfo { hasNextPage endCursor }
            edges { node { id title price inventoryItem { id sku } selectedOptions { name value } } }
            }
        }
        }
        """
        all_variants, cursor = [], None
        while True:
            data = self.shopify_graphql(query, {"productId": product_id, "cursor": cursor})
            variants_data = data["data"]["product"]["variants"]
            all_variants.extend(edge["node"] for edge in variants_data["edges"])
            page_info = variants_data["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            cursor = page_info["endCursor"]
        return all_variants

    def _patch_variants(self, product, variants, default_price, default_sku):
        all_variants = self._fetch_all_variants(product["id"])
        if not all_variants:
            return {}

        if variants:
            shared_price = next((v.get("price") for v in variants if v.get("price")), default_price)
            updates = [
                {
                    "id": cv["id"],
                    "price": str(shared_price),
                    "inventoryItem": {"sku": str(int(default_sku) + i), "tracked": False},
                    "inventoryPolicy": "CONTINUE",
                }
                for i, cv in enumerate(all_variants)
            ]
        else:
            updates = [{
                "id": all_variants[0]["id"],
                "price": str(default_price),
                "inventoryItem": {"sku": str(default_sku), "tracked": False},
                "inventoryPolicy": "CONTINUE",
            }]

        return self.shopify_graphql(
            """
            mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
            productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                productVariants { id title price inventoryItem { id sku tracked } inventoryPolicy }
                userErrors { field message }
            }
            }
            """,
            {"productId": product["id"], "variants": updates},
        )

    def _publish_to_channels(self, product_id: str, publication_ids: list[str]) -> dict:
        return self.shopify_graphql(
            """
            mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
            publishablePublish(id: $id, input: $input) {
                publishable {
                availablePublicationsCount { count }
                resourcePublicationsCount { count }
                }
                userErrors { field message }
            }
            }
            """,
            {"id": product_id, "input": [{"publicationId": pid} for pid in publication_ids]},
        )
