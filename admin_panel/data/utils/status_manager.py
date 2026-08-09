"""Zarządza komunikatami statusu w aplikacji"""

class StatusMsg:
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

    MESSAGES = {
        # General
        "LOAD_START": ("Loading data for: {}...", INFO),
        "LOAD_SUCCESS": ("View: {} loaded.", INFO),
        "DB_ERROR": ("Database error: {}.", ERROR),
        "VIEW_LOADED_COUNT": ("View: {} loaded.", SUCCESS),
        "ACTIVITY_UPDATED": ("Activity updated for: {} (Total: {}).", INFO),
        
        # Dashboard & Activity
        "STATS_UPDATED": ("Metrics updated for: {}.", INFO),
        "NO_TREND_DATA": ("KPIs updated, but no trend data available for {}.", WARNING),
        
        # Users
        "DATA_COUNT": ("Displaying {} records.", SUCCESS),
        "NO_DATA": ("No records found for: {}.", WARNING),
        "USER_DETAILS": ("Details loaded for user: {}.", INFO),
        "RESET_FILTERS": ("All filters have been reset.", INFO),
        
        # Reports
        "REPORT_GEN": ("Report '{}' generated successfully.", SUCCESS),
        "REPORT_EMPTY": ("Report '{}' for {} is empty.", WARNING),
        "EXPORT_START": ("Exporting data to CSV...", INFO),
        "EXPORT_SUCCESS": ("Report exported to: {}.", SUCCESS),
        "EXPORT_CANCEL": ("Export cancelled.", INFO),
        "EXPORT_NONE": ("Nothing to export. Generate a report first.", WARNING),
    }

    @staticmethod
    def get(key, *args):
        template, level = StatusMsg.MESSAGES.get(key, ("{}", "info"))
        try:
            return template.format(*args), level
        except:
            return template, level
