
import json
import os

class AppConnector:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.applications = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_file):
            # Tạo file config.json rỗng nếu chưa tồn tại
            with open(self.config_file, "w") as f:
                json.dump({"applications": []}, f, indent=4)
            return []
        with open(self.config_file, "r") as f:
            return json.load(f).get("applications", [])

    def get_app_config(self, app_name: str) -> dict or None:
        """
        Lấy cấu hình của một ứng dụng dựa trên tên ứng dụng.
        """
        for app in self.applications:
            if app.get("app_name") == app_name:
                return app
        return None

    def add_app_config(self, app_data: dict):
        """
        Thêm cấu hình cho một ứng dụng mới.
        """
        if self.get_app_config(app_data.get("app_name")):
            print(f"Ứng dụng {app_data.get("app_name")} đã tồn tại. Vui lòng cập nhật thay vì thêm mới.")
            return False
        self.applications.append(app_data)
        self._save_config()
        return True

    def update_app_config(self, app_name: str, new_data: dict):
        """
        Cập nhật cấu hình của một ứng dụng hiện có.
        """
        for i, app in enumerate(self.applications):
            if app.get("app_name") == app_name:
                self.applications[i].update(new_data)
                self._save_config()
                return True
        print(f"Ứng dụng {app_name} không tìm thấy để cập nhật.")
        return False

    def delete_app_config(self, app_name: str):
        """
        Xóa cấu hình của một ứng dụng.
        """
        initial_len = len(self.applications)
        self.applications = [app for app in self.applications if app.get("app_name") != app_name]
        if len(self.applications) < initial_len:
            self._save_config()
            return True
        print(f"Ứng dụng {app_name} không tìm thấy để xóa.")
        return False

    def _save_config(self):
        with open(self.config_file, "w") as f:
            json.dump({"applications": self.applications}, f, indent=4)


