"""
This file contains all the unit tests for our describe support.
"""
from pathlib import Path

# noinspection PyProtectedMember
from builder.java.describe import JavaClass, _group_class_file_names, _parse_class_info_output, _run_describer, \
    describe_classes
from tests.test_support import get_test_path, FakeProcessContext, FakeProcess, Options


class TestJavaClassObject(object):
    @staticmethod
    def _load_and_test(file_name: str, expected_type: str, expected_name: str, is_entry_point: bool):
        path = get_test_path(f'java/javap/{file_name}.txt')
        content = path.read_text('UTF-8')
        java_class = JavaClass(content.split('\n')[1:])

        assert java_class.type() == expected_type
        assert java_class.name() == expected_name
        assert java_class.is_entry_point() == is_entry_point

    def test_java_class_object_class_no_entry_point(self):
        """
        Make sure our Java object constructs correctly from a class description with no
        entry point.
        """
        self._load_and_test('one-class-no-main', 'class', 'com.example.ui.UIUtils', False)

    def test_java_class_object_interface_no_entry_point(self):
        """
        Make sure our Java object constructs correctly from an interface description
        with no entry point.
        """
        self._load_and_test('one-interface-no-main', 'interface', 'com.example.ui.UIUtils', False)

    def test_java_class_object_class_with_entry_point(self):
        """
        Make sure our Java object constructs correctly from a class description with no
        entry point.
        """
        self._load_and_test('one-class-with-main', 'class', 'com.example.ui.UIUtils', True)

    def test_java_class_object_interface_with_entry_point(self):
        """
        Make sure our Java object constructs correctly from an interface description
        with no entry point.
        """
        self._load_and_test('one-interface-with-main', 'interface', 'com.example.ui.UIUtils', False)


class TestPathGrouping(object):
    def test_path_grouping_one_group(self):
        """Make sure we get the right thing when all paths fit in one set."""
        paths = [Path('My.class')]
        groups = _group_class_file_names(paths)

        assert len(groups) == 1
        assert groups[0] == paths

        paths = [Path('My.class'), Path('Your.class')]
        groups = _group_class_file_names(paths)

        assert len(groups) == 1
        assert groups[0] == paths

    def test_path_grouping_multiple_groups(self):
        """Make sure we get the right thing when paths need to split across groups."""
        paths = [Path(f'Class{index}.class') for index in range(9)]
        groups = _group_class_file_names(paths, max_length=50)

        assert len(groups) == 3
        assert groups[0] == paths[:3]
        assert groups[1] == paths[3:7]
        assert groups[2] == paths[7:]


class TestJavaPLineParsing(object):
    def test_javap_output_parsing(self):
        """
        Make sure we can take output with many class descriptions and parse them
        correctly.
        """
        path = get_test_path(f'java/javap/many-classes.txt')
        content = path.read_text('UTF-8').split('\n')
        classes = []
        expected = [
            ('class', 'com.example.ui.UIUtils', False),
            ('class', 'com.example.App', True),
            ('class', 'com.example.Frame', False),
            ('interface', 'com.example.ui.Worker', False)
        ]
        _parse_class_info_output(content, classes)

        assert len(classes) == len(expected)

        for index, java_class in enumerate(classes):
            expected_type, expected_name, expected_is_ep = expected[index]
            assert java_class.type() == expected_type
            assert java_class.name() == expected_name
            assert java_class.is_entry_point() == expected_is_ep


class TestRunJavaP(object):
    def test_run_javap_no_public(self):
        directory = Path('.')
        class_file = Path('MyClass.class')
        expected_args = ['javap', str(class_file)]

        with FakeProcessContext(FakeProcess(expected_args, "line 1\nline 2", cwd=directory)):
            result = _run_describer(directory, [class_file], False)

        assert result == ['line 1', 'line 2']

    def test_run_javap_with_public(self):
        directory = Path('.')
        class_file = Path('MyClass.class')
        expected_args = ['javap', '-public', str(class_file)]

        with FakeProcessContext(FakeProcess(expected_args, "line 1\nline 2", cwd=directory)):
            result = _run_describer(directory, [class_file], True)

        assert result == ['line 1', 'line 2']

    def test_run_javap_with_verbose(self):
        directory = Path('.')
        class_file = Path('MyClass.class')
        expected_args = ['javap', '-verbose', str(class_file)]

        with Options(verbose=3):
            with FakeProcessContext(FakeProcess(expected_args, "line 1\nline 2", cwd=directory)):
                result = _run_describer(directory, [class_file], False)

        assert result == ['line 1', 'line 2']

    def test_run_javap_with_public_verbose(self):
        directory = Path('.')
        class_file = Path('MyClass.class')
        expected_args = ['javap', '-verbose', '-public', str(class_file)]

        with Options(verbose=3):
            with FakeProcessContext(FakeProcess(expected_args, "line 1\nline 2", cwd=directory)):
                result = _run_describer(directory, [class_file], True)

        assert result == ['line 1', 'line 2']


class TestDescribeClasses(object):
    def test_describe_classes_no_classes(self):
        directory = get_test_path('java/javap')

        with FakeProcessContext([]):
            result = describe_classes(directory, True)

        assert len(result) == 0

    def test_describe_classes_with_classes(self):
        directory = get_test_path('java/classes')
        class_file = Path('Fake.class')
        stdout = get_test_path('java/javap/one-class-with-main.txt')
        expected_args = ['javap', '-public', str(class_file)]

        with FakeProcessContext(FakeProcess(expected_args, stdout)):
            result = describe_classes(directory, True)

        assert len(result) == 1

        java_class = result[0]

        assert isinstance(java_class, JavaClass)
        assert java_class.type() == 'class'
        assert java_class.name() == 'com.example.ui.UIUtils'
        assert java_class.is_entry_point()
