"""
モジュールスコープでのクラス参照（エイリアス）の問題をテストする

このテストは、モジュールレベルでクラスをエイリアスした場合、
リロード後にエイリアスが新しいクラスを参照するか確認します。
"""

import textwrap

from .test_utils import create_test_modules, update_module


def test_class_alias_problem(tmp_path):
    """モジュールスコープでのクラス参照（エイリアス）を検証"""

    # テスト用パッケージを作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'custom_class.py': textwrap.dedent(
                '''
                class MyClass:
                    """カスタムクラス v1"""
                    VERSION = 1

                    def get_version(self):
                        return self.VERSION

                # モジュールスコープでエイリアスを作成
                MyAlias = MyClass
            '''
            ),
        },
    )

    # 初回インポート
    import custom_class  # type: ignore

    # リロード前の確認
    obj_from_class = custom_class.MyClass()
    obj_from_alias = custom_class.MyAlias()

    version_class_before = obj_from_class.get_version()
    version_alias_before = obj_from_alias.get_version()
    class_id_before = id(custom_class.MyClass)
    alias_id_before = id(custom_class.MyAlias)

    assert version_class_before == 1
    assert version_alias_before == 1
    assert custom_class.MyClass is custom_class.MyAlias

    # custom_class.pyを更新
    update_module(
        modules_dir,
        'custom_class.py',
        textwrap.dedent(
            '''
            class MyClass:
                """カスタムクラス v2"""
                VERSION = 2

                def get_version(self):
                    return self.VERSION

            # モジュールスコープでエイリアスを作成
            MyAlias = MyClass
        '''
        ),
    )

    # deep_reloadでリロード
    from deep_reloader import deep_reload

    deep_reload(custom_class)

    # リロード後の確認
    obj_from_class = custom_class.MyClass()
    obj_from_alias = custom_class.MyAlias()

    version_class_after = obj_from_class.get_version()
    version_alias_after = obj_from_alias.get_version()
    class_id_after = id(custom_class.MyClass)
    alias_id_after = id(custom_class.MyAlias)

    # 検証: バージョンが更新されている
    assert version_class_after == 2, f'MyClass.VERSIONが更新されていません: {version_class_after}'
    assert version_alias_after == 2, f'MyAlias.VERSIONが更新されていません: {version_alias_after}'

    # 検証: クラスIDが変更されている（新しいクラスオブジェクトが作成された）
    assert class_id_before != class_id_after, 'MyClassのIDが変更されていません'
    assert alias_id_before != alias_id_after, 'MyAliasのIDが変更されていません'

    # 検証: MyClassとMyAliasは同一オブジェクト
    assert custom_class.MyClass is custom_class.MyAlias, 'MyClassとMyAliasが同一オブジェクトではありません'
