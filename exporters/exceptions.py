class ExportBaseError(Exception):
    pass

class FileWriteError(ExportBaseError):
    pass

class InvalidDataError(ExportBaseError):
    pass