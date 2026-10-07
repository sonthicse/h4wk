from abc import ABC, abstractmethod


class BaseCollector(ABC):
    """Giao diện collector độc lập với công cụ và schema dữ liệu."""

    @abstractmethod
    def collect(self, target_url):
        """Thu thập dữ liệu từ URL và trả về kết quả do lớp con định nghĩa.

        Lớp con quy định kiểu, schema và cách chuẩn hoá kết quả.
        Lỗi được ném ra cho bên gọi xử lý, không trả về như dữ liệu thành công.
        """
        raise NotImplementedError
