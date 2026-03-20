#!/usr/bin/env python3
"""tasks_tool.py 单元测试。

运行方式:
  cd scripts/
  python -m pytest test_tasks_tool.py -v
  # 或直接:
  python test_tasks_tool.py
"""

import json
import os
import sys
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

# 确保能导入 tasks_tool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tasks_tool


class BaseTestCase(unittest.TestCase):
    """基础测试类：每个测试用例使用临时目录，不污染真实数据。"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_tasks_dir = tasks_tool.TASKS_DIR
        self.original_tasks_file = tasks_tool.TASKS_FILE
        tasks_tool.TASKS_DIR = self.test_dir
        tasks_tool.TASKS_FILE = os.path.join(self.test_dir, "tasks.json")

    def tearDown(self):
        tasks_tool.TASKS_DIR = self.original_tasks_dir
        tasks_tool.TASKS_FILE = self.original_tasks_file
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _load(self):
        with open(tasks_tool.TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)


class TestResolveDate(BaseTestCase):
    """测试日期解析。"""

    def test_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(tasks_tool._resolve_date("today"), today)
        self.assertEqual(tasks_tool._resolve_date("今天"), today)

    def test_tomorrow(self):
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        self.assertEqual(tasks_tool._resolve_date("tomorrow"), tomorrow)
        self.assertEqual(tasks_tool._resolve_date("明天"), tomorrow)

    def test_day_after_tomorrow(self):
        dat = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        self.assertEqual(tasks_tool._resolve_date("后天"), dat)

    def test_iso_format(self):
        self.assertEqual(tasks_tool._resolve_date("2026-03-25"), "2026-03-25")

    def test_short_format(self):
        year = datetime.now().year
        result = tasks_tool._resolve_date("12-25")
        self.assertIn("12-25", result)

    def test_none(self):
        self.assertIsNone(tasks_tool._resolve_date(None))
        self.assertIsNone(tasks_tool._resolve_date(""))


class TestAdd(BaseTestCase):
    """测试添加待办。"""

    def test_basic_add(self):
        tasks_tool.cmd_add(["买牛奶", "--target", "reminder"])
        data = self._load()
        self.assertEqual(len(data["tasks"]), 1)
        self.assertEqual(data["tasks"][0]["title"], "买牛奶")
        self.assertEqual(data["tasks"][0]["target"], "reminder")
        self.assertEqual(data["tasks"][0]["status"], "pending")

    def test_add_with_date_auto_prefix(self):
        """核心测试：有 --date 时 title 自动加日期前缀。"""
        tomorrow = (datetime.now() + timedelta(days=1))
        expected_prefix = f"{tomorrow.month}月{tomorrow.day}日"

        tasks_tool.cmd_add(["跳舞", "--date", "tomorrow", "--target", "reminder"])
        data = self._load()
        title = data["tasks"][0]["title"]
        self.assertTrue(title.startswith(expected_prefix), f"标题 '{title}' 应以 '{expected_prefix}' 开头")
        self.assertIn("跳舞", title)

    def test_add_with_date_no_duplicate_prefix(self):
        """title 已有日期前缀时不重复添加。"""
        tomorrow = (datetime.now() + timedelta(days=1))
        prefix = f"{tomorrow.month}月{tomorrow.day}日"

        tasks_tool.cmd_add([f"{prefix} 跳舞", "--date", "tomorrow", "--target", "reminder"])
        data = self._load()
        title = data["tasks"][0]["title"]
        # 确保不会变成 "3月21日 3月21日 跳舞"
        self.assertEqual(title, f"{prefix} 跳舞")

    def test_add_without_date_no_prefix(self):
        """无 --date 时 title 不加日期前缀。"""
        tasks_tool.cmd_add(["洗车", "--target", "reminder"])
        data = self._load()
        self.assertEqual(data["tasks"][0]["title"], "洗车")

    def test_add_note_no_prefix(self):
        """备忘录类型不加日期前缀（即使有 --date）。"""
        tasks_tool.cmd_add(["读书笔记", "--date", "tomorrow", "--target", "note", "--notes", "第三章要点"])
        data = self._load()
        self.assertEqual(data["tasks"][0]["title"], "读书笔记")
        self.assertEqual(data["tasks"][0]["notes"], "第三章要点")

    def test_add_with_time(self):
        tasks_tool.cmd_add(["开会", "--date", "tomorrow", "--time", "14:00", "--target", "reminder"])
        data = self._load()
        self.assertEqual(data["tasks"][0]["time"], "14:00")

    def test_add_with_priority(self):
        tasks_tool.cmd_add(["紧急任务", "--priority", "high", "--target", "reminder"])
        data = self._load()
        self.assertEqual(data["tasks"][0]["priority"], "high")

    def test_add_default_priority(self):
        tasks_tool.cmd_add(["普通任务"])
        data = self._load()
        self.assertEqual(data["tasks"][0]["priority"], "medium")

    def test_add_multiple(self):
        tasks_tool.cmd_add(["任务1"])
        tasks_tool.cmd_add(["任务2"])
        tasks_tool.cmd_add(["任务3"])
        data = self._load()
        self.assertEqual(len(data["tasks"]), 3)

    def test_add_today_prefix(self):
        """今天的日期前缀。"""
        today = datetime.now()
        expected_prefix = f"{today.month}月{today.day}日"

        tasks_tool.cmd_add(["开会", "--date", "today", "--target", "reminder"])
        data = self._load()
        title = data["tasks"][0]["title"]
        self.assertTrue(title.startswith(expected_prefix))

    def test_add_specific_date_prefix(self):
        """指定具体日期的前缀。"""
        tasks_tool.cmd_add(["体检", "--date", "2026-04-15", "--target", "reminder"])
        data = self._load()
        title = data["tasks"][0]["title"]
        self.assertTrue(title.startswith("4月15日"))


class TestDone(BaseTestCase):
    """测试标记完成。"""

    def test_mark_done(self):
        tasks_tool.cmd_add(["测试任务"])
        data = self._load()
        task_id = data["tasks"][0]["id"]

        tasks_tool.cmd_done([task_id])
        data = self._load()
        self.assertEqual(data["tasks"][0]["status"], "done")

    def test_done_nonexistent(self):
        """标记不存在的 ID 不报错。"""
        tasks_tool.cmd_add(["测试任务"])
        tasks_tool.cmd_done(["nonexistent"])
        data = self._load()
        self.assertEqual(data["tasks"][0]["status"], "pending")


class TestRemove(BaseTestCase):
    """测试删除。"""

    def test_remove(self):
        tasks_tool.cmd_add(["要删的任务"])
        data = self._load()
        task_id = data["tasks"][0]["id"]

        tasks_tool.cmd_remove([task_id])
        data = self._load()
        self.assertEqual(len(data["tasks"]), 0)

    def test_remove_nonexistent(self):
        tasks_tool.cmd_add(["保留的任务"])
        tasks_tool.cmd_remove(["nonexistent"])
        data = self._load()
        self.assertEqual(len(data["tasks"]), 1)


class TestEdit(BaseTestCase):
    """测试编辑。"""

    def test_edit_title(self):
        tasks_tool.cmd_add(["旧标题"])
        data = self._load()
        task_id = data["tasks"][0]["id"]

        tasks_tool.cmd_edit([task_id, "--title", "新标题"])
        data = self._load()
        self.assertEqual(data["tasks"][0]["title"], "新标题")

    def test_edit_date(self):
        tasks_tool.cmd_add(["任务", "--date", "today"])
        data = self._load()
        task_id = data["tasks"][0]["id"]

        tasks_tool.cmd_edit([task_id, "--date", "tomorrow"])
        data = self._load()
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        self.assertEqual(data["tasks"][0]["date"], tomorrow)

    def test_edit_priority(self):
        tasks_tool.cmd_add(["任务"])
        data = self._load()
        task_id = data["tasks"][0]["id"]

        tasks_tool.cmd_edit([task_id, "--priority", "high"])
        data = self._load()
        self.assertEqual(data["tasks"][0]["priority"], "high")


class TestList(BaseTestCase):
    """测试列表。"""

    def test_list_empty(self):
        """空列表不报错。"""
        tasks_tool.cmd_list([])

    def test_list_all(self):
        tasks_tool.cmd_add(["任务1", "--date", "today"])
        tasks_tool.cmd_add(["任务2", "--date", "tomorrow"])
        tasks_tool.cmd_list([])

    def test_list_by_date(self):
        tasks_tool.cmd_add(["今天的", "--date", "today"])
        tasks_tool.cmd_add(["明天的", "--date", "tomorrow"])
        # 按今天过滤
        tasks_tool.cmd_list(["--date", "today"])

    def test_list_by_status(self):
        tasks_tool.cmd_add(["任务1"])
        data = self._load()
        task_id = data["tasks"][0]["id"]
        tasks_tool.cmd_done([task_id])

        tasks_tool.cmd_add(["任务2"])
        tasks_tool.cmd_list(["--status", "pending"])

    def test_list_by_target(self):
        tasks_tool.cmd_add(["提醒", "--target", "reminder"])
        tasks_tool.cmd_add(["笔记", "--target", "note"])
        tasks_tool.cmd_list(["--target", "note"])


class TestClear(BaseTestCase):
    """测试清理。"""

    def test_clear_done(self):
        tasks_tool.cmd_add(["完成的"])
        tasks_tool.cmd_add(["未完成的"])
        data = self._load()
        tasks_tool.cmd_done([data["tasks"][0]["id"]])

        tasks_tool.cmd_clear(["--done"])
        data = self._load()
        self.assertEqual(len(data["tasks"]), 1)
        self.assertEqual(data["tasks"][0]["title"], "未完成的")

    def test_clear_before_date(self):
        tasks_tool.cmd_add(["旧任务", "--date", "2026-01-01"])
        tasks_tool.cmd_add(["新任务", "--date", "2026-12-31"])

        tasks_tool.cmd_clear(["--before", "2026-06-01"])
        data = self._load()
        self.assertEqual(len(data["tasks"]), 1)
        self.assertEqual(data["tasks"][0]["date"], "2026-12-31")


class TestShow(BaseTestCase):
    """测试 JSON 输出。"""

    def test_show(self):
        tasks_tool.cmd_add(["测试"])
        tasks_tool.cmd_show([])


class TestParseOpts(unittest.TestCase):
    """测试参数解析。"""

    def test_basic(self):
        opts = tasks_tool._parse_opts(["--date", "tomorrow", "--time", "14:00"])
        self.assertEqual(opts["date"], "tomorrow")
        self.assertEqual(opts["time"], "14:00")

    def test_empty(self):
        opts = tasks_tool._parse_opts([])
        self.assertEqual(opts, {})

    def test_single(self):
        opts = tasks_tool._parse_opts(["--priority", "high"])
        self.assertEqual(opts["priority"], "high")


class TestDatePrefixEdgeCases(BaseTestCase):
    """日期前缀的边界情况测试。"""

    def test_date_prefix_with_chinese_date_in_title(self):
        """用户自己在标题中写了日期。"""
        tasks_tool.cmd_add(["3月25日 看电影", "--date", "2026-03-25", "--target", "reminder"])
        data = self._load()
        # 不应重复添加
        self.assertEqual(data["tasks"][0]["title"], "3月25日 看电影")

    def test_date_prefix_format(self):
        """验证日期前缀格式：X月X日（不带零）。"""
        tasks_tool.cmd_add(["约会", "--date", "2026-01-05", "--target", "reminder"])
        data = self._load()
        title = data["tasks"][0]["title"]
        self.assertTrue(title.startswith("1月5日"), f"期望 '1月5日' 开头，实际: '{title}'")

    def test_multiple_tasks_different_dates(self):
        """多个任务不同日期都有正确前缀。"""
        tasks_tool.cmd_add(["跳舞", "--date", "tomorrow", "--target", "reminder"])
        tasks_tool.cmd_add(["唱歌", "--date", "2026-03-24", "--target", "reminder"])
        tasks_tool.cmd_add(["画画", "--target", "reminder"])  # 无日期

        data = self._load()
        tomorrow = datetime.now() + timedelta(days=1)

        # 跳舞：有日期前缀
        self.assertTrue(data["tasks"][0]["title"].startswith(f"{tomorrow.month}月{tomorrow.day}日"))
        # 唱歌：有日期前缀
        self.assertTrue(data["tasks"][1]["title"].startswith("3月24日"))
        # 画画：无日期前缀
        self.assertEqual(data["tasks"][2]["title"], "画画")


class TestUpdatedAt(BaseTestCase):
    """测试 updated_at 字段。"""

    def test_updated_at_set(self):
        tasks_tool.cmd_add(["测试"])
        data = self._load()
        self.assertIsNotNone(data["updated_at"])
        # 验证格式
        datetime.strptime(data["updated_at"], "%Y-%m-%dT%H:%M:%S")

    def test_updated_at_changes(self):
        tasks_tool.cmd_add(["任务1"])
        data1 = self._load()
        ts1 = data1["updated_at"]

        import time
        time.sleep(1)

        tasks_tool.cmd_add(["任务2"])
        data2 = self._load()
        ts2 = data2["updated_at"]

        self.assertGreaterEqual(ts2, ts1)


class TestGenId(unittest.TestCase):
    """测试 ID 生成。"""

    def test_unique(self):
        ids = {tasks_tool._gen_id() for _ in range(100)}
        self.assertEqual(len(ids), 100)

    def test_length(self):
        self.assertEqual(len(tasks_tool._gen_id()), 8)

    def test_hex(self):
        id_ = tasks_tool._gen_id()
        int(id_, 16)  # 应该是合法的十六进制


if __name__ == "__main__":
    unittest.main(verbosity=2)
