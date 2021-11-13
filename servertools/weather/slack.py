from datetime import datetime
from typing import List
import pandas as pd
from kavalkilu import LogWithInflux
from slacktools import BlockKitBuilder as bkb
from ..slack_communicator import SlackComm


class SlackWeatherNotification:
    def __init__(self, parent_log: LogWithInflux):
        self.sComm = SlackComm(parent_log=parent_log)

    @staticmethod
    def _format_severe_alert_text(alert_row: pd.Series) -> str:
        """Formats the row of alerts into a string"""
        alert_dict = alert_row.to_dict()
        alert_txt = "*`{event}`* ({severity})\t\t`{start}` to `{end}`\n" \
                    "*{title}*\n{desc}".format(**alert_dict)
        return alert_txt

    def _notify_channel(self, alert_blocks: List[dict], channel: str, title: str):
        """Wrapper function to send alert to notification channel"""
        self.sComm.st.send_message(channel=channel, message=title, blocks=alert_blocks)

    def severe_weather_alert(self, alert_df: pd.DataFrame):
        """Formats a severe weather notification for Slack & sends it"""
        alert_list = []
        for idx, row in alert_df.iterrows():
            alert_list.append(self._format_severe_alert_text(row))

        alert_blocks = [
            bkb.make_context_section(f'{len(alert_list)} Incoming alert(s) <@{self.sComm.user_me}>!'),
            bkb.make_block_divider(),
            bkb.make_block_section(alert_list)
        ]
        self._notify_channel(alert_blocks, channel=self.sComm.hoiatuste_kanal, title='Incoming weather alert!')

    def frost_alert(self, warning: str, lowest_temp: float, highest_wind: float):
        """Handles routines for alerting to a frost warning"""
        blocks = [
            bkb.make_context_section(f'Frost/Freeze Alert <@{self.sComm.user_me}>!'),
            bkb.make_block_divider(),
            bkb.make_block_section(f'{warning.title()} Warning: *`{lowest_temp:.1f}C`* *`{highest_wind:.1f}m/s`*')
        ]
        self._notify_channel(blocks, channel=self.sComm.hoiatuste_kanal, title='Frost/Freeze Alert!')

    def sig_temp_change_alert(self, temp_diff: float, apptemp_diff: float, temp_dict: dict):
        """Handles routines for alerting a singificant change in temperature"""
        msg_text = f'Temp higher at midnight `{temp_dict[0]["temp"]:.2f} ({temp_dict[0]["apptemp"]:.2f})` ' \
                   f'than midday `{temp_dict[12]["temp"]:.2f} ({temp_dict[12]["apptemp"]:.2f})` '\
                   f'diff: `{temp_diff:.1f} ({apptemp_diff:.1f})`'
        blocks = [
            bkb.make_context_section(f'Significant Temp Change Alert <@{self.sComm.user_me}>!'),
            bkb.make_block_divider(),
            bkb.make_block_section(msg_text)
        ]
        self._notify_channel(blocks, channel=self.sComm.hoiatuste_kanal, title='Sig Temp Change Alert!')

    def daily_weather_briefing(self, tomorrow: datetime, report: List[str]):
        """Presents a daily weather report for the work week"""
        blocks = [
            bkb.make_context_section(f'*Weather Report for {tomorrow:%A, %d %B}*'),
            bkb.make_block_divider(),
            bkb.make_block_section(report)
        ]
        self._notify_channel(blocks, channel=self.sComm.ilma_kanal, title='Weather Report')
