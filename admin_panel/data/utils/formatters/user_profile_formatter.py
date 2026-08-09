"""Formatery dla profilu użytkownika

Zawiera funkcje do formatowania HTML profilu wyświetlanego w widoku users
"""


class UserProfileFormatter:
    """Formatuje HTML profilu użytkownika do wyświetlenia w widoku"""

    @staticmethod
    def format_profile(profile, user_ppd, system_avg, current_filter):
        """Formatuje HTML profilu użytkownika"""
        full_name = profile.get("name", "Unknown")
        username = profile.get("username", "unknown")
        streak = profile["streak"]
        streak_text = f"🔥 {streak} DAYS" if streak > 0 else "❄️ NO STREAK"
        streak_color = "#e67e22" if streak > 0 else "#95a5a6"

        # Consistency score
        consistency = profile.get("consistency_score", 0)
        if consistency >= 80:
            consistency_color = "#27ae60"
            consistency_label = "EXCELLENT"
        elif consistency >= 50:
            consistency_color = "#3498db"
            consistency_label = "GOOD"
        elif consistency >= 20:
            consistency_color = "#f39c12"
            consistency_label = "FAIR"
        else:
            consistency_color = "#e74c3c"
            consistency_label = "POOR"

        # Performance status
        diff = user_ppd - system_avg
        if diff > 1.0:
            perf_status = "<b style='color: #27ae60;'>▲ ABOVE AVG</b>"
            ppd_color = "#27ae60"
        elif diff < -1.0:
            perf_status = "<b style='color: #e67e22;'>▼ BELOW AVG</b>"
            ppd_color = "#e67e22"
        else:
            perf_status = "<b style='color: #3498db;'>≈ ON PAR</b>"
            ppd_color = "#3498db"

        reading_potential = profile["potential_ppd"]
        progress = profile["avg_progress"]
        total_pages = profile["total_pages"]
        reading_list = profile["reading_now"] if profile["reading_now"] else []
        user_status = profile.get("status", "active")
        reading_str = (
            ", ".join(f"{i+1}. {book}" for i, book in enumerate(reading_list))
            if reading_list
            else ("None (inactive account)" if user_status == "inactive" else "None")
        )
        filter_label = (
            f"({current_filter.upper()})"
            if current_filter.lower() != "all"
            else "(ALL TIME)"
        )

        return (
            f"<div style='font-family: Segoe UI, sans-serif; padding: 10px; color: #2c3e50;'>"
            f"  <div style='border-bottom: 2px solid #2c3e50; padding-bottom: 5px; margin-bottom: 15px;'>"
            f"      <table width='100%'><tr>"
            f"          <td>"
            f"              <span style='font-size: 18px;'><b>{full_name.upper()}</b></span> "
            f"              <span style='color: #7f8c8d; font-size: 13px; margin-left: 5px;'>(@{username})</span>"
            f"          </td>"
            f"          <td align='right' style='font-size: 13px; color: #7f8c8d;'>"
            f"              <b>EXT-ID: {profile['ext_id']}</b> &nbsp;|&nbsp; "
            f"              <b style='color: {streak_color};'>{streak_text}</b> &nbsp;|&nbsp; "
            f"              <b style='color: {consistency_color};'>{consistency:.0f}% {consistency_label}</b>"
            f"          </td>"
            f"      </tr></table>"
            f"  </div>"
            f"  <table width='100%' style='margin-bottom: 20px;' cellpadding='0' cellspacing='0'><tr>"
            f"      <td width='30%' style='vertical-align: top; border-right: 1px dotted #dcdfe3; padding-right: 15px;'>"
            f"          <div style='color: #7f8c8d; font-size: 10px; margin-bottom: 5px;'>ACCOUNT INFO</div>"
            f"          <div style='font-size: 12px; line-height: 1.6;'>"
            f"              👤 <b>AGE:</b> {profile['age']}<br>"
            f"              📅 <b>JOINED:</b> {profile['date_joined'][:10]}<br>"
            f"              🕒 <b>LAST ACTIVITY:</b> {profile['last_activity'][:16] if profile['last_activity'] else 'Never'}"
            f"          </div>"
            f"      </td>"
            f"      <td width='35%' style='vertical-align: top; border-right: 1px dotted #dcdfe3; padding-left: 15px; padding-right: 15px;' align='center'>"
            f"          <div style='color: #7f8c8d; font-size: 11px; margin-bottom: 5px;'>CURRENT PERFORMANCE {filter_label}</div>"
            f"          <div style='font-size: 28px; color: {ppd_color};'><b>{user_ppd:.1f}</b> <small style='font-size: 14px;'>PPD</small></div>"
            f"          <div style='font-size: 12px; margin-top: 4px;'>{perf_status} <span style='color: #95a5a6;'>(AVG: {system_avg:.1f})</span></div>"
            f"      </td>"
            f"      <td width='35%' style='vertical-align: top; padding-left: 15px;' align='center'>"
            f"          <div style='color: #7f8c8d; font-size: 11px; margin-bottom: 5px;'>CHALLENGE PROGRESS & POTENTIAL</div>"
            f"          <div style='font-size: 28px; color: #3498db;'><b>{progress}%</b></div>"
            f"          <div style='font-size: 12px; margin-top: 4px; color: #2c3e50;'>"
            f"              <b>Potential:</b> {reading_potential:.1f} active ppd<br>"
            f"              <b>Total Pages Read:</b> {total_pages}"
            f"          </div>"
            f"      </td>"
            f"  </tr></table>"
            f"  <div style='background-color: #f8f9fa; padding: 10px; border-radius: 4px; border: 1px solid #e9ecef;'>"
            f"      <div style='font-size: 12px; color: #2c3e50; margin-bottom: 8px;'>📚 <b>CURRENTLY READING:</b> <span style='color: #27ae60; font-weight: bold;'>{reading_str.upper()}</span></div>"
            f"      <div style='border-top: 1px solid #dee2e6; padding-top: 6px; color: #7f8c8d; font-size: 10px; line-height: 1.4;'>"
            f"          <b>Reading Potential:</b> Average PPD from days with logged activity (activity-based).<br>"
            f"          <b>Performance {filter_label}:</b> Average PPD in selected period (time-based). Benchmark: last 30 days avg of all active users.<br>"
            f"          <b>Consistency Score:</b> % of active days in last 30 days. <span style='color: #27ae60;'>≥80% EXCELLENT</span> | <span style='color: #3498db;'>50-79% GOOD</span> | <span style='color: #f39c12;'>20-49% FAIR</span> | <span style='color: #e74c3c;'>&lt;20% POOR</span>"
            f"      </div>"
            f"  </div>"
            f"</div>"
        )
