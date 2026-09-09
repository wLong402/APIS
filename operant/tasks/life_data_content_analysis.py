# -*- coding: utf-8 -*-
"""抖音生活服务生意经：内容分析 → 昨日 → 抖音列表 → 导出 Excel。"""

from operant.registry import register_task
from operant.task import OperantTask

LOGIN_URL = (
    'https://www.life-data.cn/flow/content/my/overview'
    '?groupid=1768672137314371'
)
SAVE_AS = r'D:\downloads\测试.xlsx'


def _build_mission(start: str, end: str, extras: dict) -> str:
    extra = extras.get('instruction') or ''
    return f'''按下面步骤操作，不要跳步，不要改日期。

1. 打开网页：{LOGIN_URL}
   如果出现登录页，用提供的帐号登录，登录成功后再继续。
2. 把鼠标悬停在顶部或侧栏的「流量」上（不要直接离开页面）。
   出现菜单后点击「内容分析」。
3. 页面右侧找到「自定义」，点击它打开日期范围选择器。
4. 在日期选择器里只选昨日：{start}（开始和结束都是这一天）。
   确认后关闭选择器。
5. 向下滚动页面，直到出现「抖音列表」。
6. 点击「抖音列表」。
7. 点击「导出数据」，等待 Excel 下载完成。
8. 把下载文件保存为：{SAVE_AS}
   如果浏览器自动下到 D:\\downloads，下载完成后把文件重命名/另存为「测试.xlsx」。

{extra}

完成后结束任务。不要在回复里写出密码或完整帐号。
'''


register_task(OperantTask(
    name='life_data_content_analysis',
    label='生意经内容分析导出',
    description='打开生活服务生意经，悬停流量→内容分析→自定义选昨日→抖音列表→导出到 D:\\downloads\\测试.xlsx',
    target_table='life_data_content_analysis',
    unique_key='rowKey',
    login_url=LOGIN_URL,
    download_dir=r'D:\downloads',
    save_as=SAVE_AS,
    default_yesterday=True,
    max_steps=50,
    build_mission=_build_mission,
))
