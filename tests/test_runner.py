"""
全テストファイルを一括でスクリプト実行するスクリプト
"""

# TODO: テストファイルの構造リファクタリング
# 現在、このプロジェクトは1ファイル1テスト関数という特殊な構造を採用しているが、
# 一般的なPythonプロジェクトでは1ファイルに複数のテスト関数を含める。
#
# 現状:
# - 既存の12ファイル: 1ファイル1テスト関数
# - test_reload_without_reimport.py: 1ファイル4テスト関数（新規追加）
#
# リファクタリング案:
# 1. 関連するテストを統合してファイル数を削減
#    - test_absolute_import.py (basic, chained, wildcard を統合)
#    - test_relative_import.py (same_level, parent, package, multilevel, wildcard を統合)
# 2. 新規テストは複数関数パターンを採用
# 3. test_runner.pyのサマリー表示を「テスト関数数」ベースに変更
#
# メリット:
# - 一般的なPythonプロジェクトとの一貫性
# - 関連テストのグループ化で可読性向上
# - ファイル数の削減
#
# 注意: 既存テストの統合は破壊的変更のため、慎重に検討すること

import subprocess
import sys
import textwrap
from pathlib import Path


def is_running_in_maya():
    """Maya環境で実行されているかを検知"""
    # Maya特有のモジュールの存在確認
    if 'maya.cmds' in sys.modules:
        return True

    return False


def show_maya_warning():
    """Maya環境での実行時の警告メッセージを表示"""
    print(
        textwrap.dedent(
        """
        警告: Maya環境での test_runner 実行が検出されました
        セーフティ機能により実行を停止します。

        理由: Maya環境でのテスト実行は以下の問題を引き起こす可能性があります:
          - テストファイルがMayaで開かれる危険性
          - subprocessの予期しない動作
          - Maya環境の不安定化

        対処法:
          - VSCodeから実行する
          - Python統合開発環境から実行する
          - コマンドプロンプト/PowerShellから実行する

        実行コマンド例:
          python ~/Documents/maya/scripts/deep_reloader/tests/test_runner.py
        """
        )
    )


def run_all_tests():
    """全テストファイルを順次実行"""
    # Maya環境での実行をブロック
    if is_running_in_maya():
        show_maya_warning()
        return False

    # 現在のディレクトリを取得
    current_dir = Path(__file__).parent

    # test_*.py パターンのファイルを自動検出
    test_files = sorted(
        [
            f.name
            for f in current_dir.glob('test_*.py')
            if f.is_file() and f.name not in ['test_utils.py', 'test_runner.py']  # 除外ファイル
        ]
    )

    print("全テストファイルのスクリプト実行を開始...")
    print(f"検出されたテストファイル: {len(test_files)}個")
    print("=" * 50)

    passed = 0
    failed = 0

    for test_file in test_files:
        test_path = current_dir / test_file

        print(f"\n実行中: {test_file}")
        print("-" * 30)

        try:
            # Pythonプロセスでテストファイルを実行
            result = subprocess.run(
                [sys.executable, str(test_path)], cwd=str(current_dir), capture_output=True, text=True, timeout=30
            )

            # 結果を表示
            if result.returncode == 0:
                print(f"OK: {test_file}: 成功")
                if result.stdout:
                    print(f"   出力: {result.stdout.strip()}")
                passed += 1
            else:
                print(f"NG: {test_file}: 失敗 (終了コード: {result.returncode})")
                if result.stderr:
                    print(f"   エラー: {result.stderr.strip()}")
                if result.stdout:
                    print(f"   出力: {result.stdout.strip()}")
                failed += 1

        except subprocess.TimeoutExpired:
            print(f"TIMEOUT: {test_file}: タイムアウト (30秒)")
            failed += 1
        except Exception as e:
            print(f"ERROR: {test_file}: 実行エラー - {e}")
            failed += 1

    # 結果サマリー
    print("\n" + "=" * 50)
    print("テスト結果サマリー:")
    print(f"   成功: {passed}")
    print(f"   失敗: {failed}")
    print(f"   合計: {passed + failed}")

    if failed == 0:
        print("\n全テスト成功!")
        return True
    else:
        print(f"\n{failed}個のテストが失敗しました")
        return False


if __name__ == "__main__":
    run_all_tests()
