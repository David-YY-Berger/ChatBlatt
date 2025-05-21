class InvalidDataError(Exception):
    def __init__(self, ref, index, errors):
        self.ref = ref
        self.index = index
        self.errors = errors
        message = f"Invalid data at index {index} for reference '{ref}': {errors}"
        super().__init__(message)
