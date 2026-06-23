"""Uniform API response envelope (success, message, data, error_code)."""


class Response:
    def __init__(self, success=False, message='', data=None, error_code=None):
        self.success = success
        self.message = message
        self.data = data if data is not None else {}
        self.error_code = error_code

    def to_dict(self):
        response_dict = {
            "success": self.success,
            "message": self.message,
            "data": self.data
        }
        if self.error_code is not None:
            response_dict["error_code"] = self.error_code
        return response_dict

    @classmethod
    def from_dict(cls, data_dict):
        return cls(
            success=data_dict.get("success", False),
            message=data_dict.get("message", ""),
            data=data_dict.get("data", {}),
            error_code=data_dict.get("error_code")
        )
