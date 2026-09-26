    def individual_product_data_extraction(self, soup: Tag) -> dict:
    
        # Variable initialization
        name: Optional[str] = None
        price: Optional[str | int] = None
        product_code: Optional[str] = None
        img: Optional[str | Any] = None
        slug: Optional[str] = None
        link: Optional[str] = None
        currency : Optional[str] = None

        # Name
        name_selector = ("h1")
        name_tag = soup.find(
            name_selector
        )
        if name_tag:
            name = name_tag.get_text(strip=True)

        # Slug
        if name is not None:
            slug = slugify(name)

        # Link
        link_selector = ("a", "ui-pdp-link")
        link_tag = soup.find(
            link_selector[0],
            class_=link_selector[1]
        )

        # Price
        price_selector = ("p", "price_color")
        price_tag = soup.find(
            price_selector[0],
            class_=price_selector[1]
        )
        if price_tag:
            price = price_tag.get_text(strip=True)
            currency = price[0]
            price = price[1:]

        # Product_id
        # Extract item_id from image_link
        product_id_selector = 'td'
        product_tag = soup.find(
            product_id_selector
        )
        if product_tag:
            product_code = product_tag.get_text(strip=True)

        # Build products
        product: dict = ({
            "name": name,
            "slug": slug,
            "price": price,
            "currency": currency,
            "product_code": product_code,
            "product_url" : link,
            "reviews" : None,
            "images": [img]
        })

        return product
