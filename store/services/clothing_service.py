from store.models.product.product import Book


class ClothingService:
    @staticmethod
    def normalize_size_options(raw_sizes: str) -> str:
        if not raw_sizes:
            return ""

        tokens = []
        seen = set()
        for token in raw_sizes.replace(";", ",").split(","):
            size = token.strip().upper()
            if not size or size in seen:
                continue
            seen.add(size)
            tokens.append(size)
        return ",".join(tokens)

    @staticmethod
    def apply_clothing_defaults(book: Book) -> None:
        if book.product_type != Book.PRODUCT_TYPE_CLOTHING:
            book.size_options = ""
            book.material = ""
            book.gender_target = ""
            if not book.author and book.brand:
                book.author = book.brand
            return

        book.size_options = ClothingService.normalize_size_options(book.size_options)
        if book.brand and not book.author:
            # Keep compatibility with places still reading author.
            book.author = book.brand
