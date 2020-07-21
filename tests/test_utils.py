"""
This file contains all the unit tests for our framework's utilities support.
"""
import os
from pathlib import Path

# noinspection PyPackageRequirements
import pytest

from builder.project import Project
from builder.utils import GlobalOptions, TempTextFile, find, get_matching_files, remove_directory, out, verbose_out, \
    labeled_out, warn, end, checked_run
from tests.test_support import get_test_path, FakeEcho, Options, FakeProcessContext, FakeProcess, ExpectedEcho


class TestGlobalOptions(object):
    def test_global_options_defaults(self):
        options = GlobalOptions()

        # noinspection PyProtectedMember
        assert len(options._vars) == 0
        assert options.project() is None

    def test_quiet(self):
        options = GlobalOptions()

        assert options.quiet() is False

        options.set_quiet(True)

        assert options.quiet() is True

    def test_verbose(self):
        options = GlobalOptions()

        assert options.verbose() == 0

        options.set_verbose(2)

        assert options.verbose() == 2

    def test_independent_tasks(self):
        options = GlobalOptions()

        assert options.independent_tasks() is False

        options.set_independent_tasks(True)

        assert options.independent_tasks() is True

    def test_force_remote_fetch(self):
        options = GlobalOptions()

        assert options.force_remote_fetch() is False

        options.set_force_remote_fetch(True)

        assert options.force_remote_fetch() is True

    def test_languages(self):
        options = GlobalOptions()
        languages = ('java', 'idea')

        assert options.languages() == ()

        options.set_languages(languages)

        assert options.languages() == languages

    def test_tasks(self):
        options = GlobalOptions()
        tasks = ('compile', 'test')

        assert options.tasks() == ()

        options.set_tasks(tasks)

        assert options.tasks() == tasks

    def test_project(self, tmpdir):
        options = GlobalOptions()
        project = Project.from_dir(Path(tmpdir))

        assert options.project() is None

        options.set_project(project)

        assert options.project() is project

    # noinspection PyProtectedMember
    def test_set_vars(self):
        options = GlobalOptions()

        # noinspection PyTypeChecker
        options.set_vars(())

        assert len(options._vars) == 0

        options.set_vars(('name',))

        assert len(options._vars) == 1

        options = GlobalOptions()

        options.set_vars(('n=v',))

        assert len(options._vars) == 1
        assert options.var('n') == 'v'

        options = GlobalOptions()

        options.set_vars(('n1=v1,n2=v2',))

        assert len(options._vars) == 2
        assert options.var('n1') == 'v1'
        assert options.var('n2') == 'v2'

        options = GlobalOptions()

        options.set_vars(('n1=v1', 'n2=v2'))

        assert len(options._vars) == 2
        assert options.var('n1') == 'v1'
        assert options.var('n2') == 'v2'

    def test_var(self, tmpdir):
        project = Project.from_dir(Path(tmpdir))
        options = GlobalOptions()

        # noinspection PyProtectedMember
        project._content['vars'] = {'n': 'project value'}

        assert options.var('n') is None

        os.environ['n'] = 'environ value'

        assert options.var('n') == 'environ value'

        options.set_project(project)

        assert options.var('n') == 'project value'

        options.set_vars(['n=pool value'])

        assert options.var('n') == 'pool value'

        os.unsetenv('n')

    def test_substitute(self):
        options = GlobalOptions()
        options.set_vars(['bob=larry'])
        extras = {'bob': 'jr'}

        assert options.substitute('${bob') == '${bob'
        assert options.substitute('$bob}') == '$bob}'
        assert options.substitute('{bob}') == '{bob}'
        assert options.substitute('${bob}') == 'larry'
        assert options.substitute('${bob2}') == ''
        assert options.substitute('${bob}', ignore_global_vars=True) == ''
        assert options.substitute('${bob}', extras=extras) == 'jr'
        assert options.substitute('${bob}/${bob}') == 'larry/larry'
        assert options.substitute('${${bob}}') == '}'
        assert options.substitute('${  bob  }') == 'larry'


class TestTempTextFile(object):
    def test_basic_temp_file_work(self):
        with TempTextFile() as file:
            path = file.file_name

            assert path.exists()

            file.write_lines(['line 1', 'line 2'])

            assert path.read_text(encoding='utf-8').split('\n') ==\
                ['line 1', 'line 2', '']

        assert not path.exists()


class TestFind(object):
    def test_find(self):
        assert find([1, 2, 3], lambda item: item == 2) == 2
        assert find([1, 2, 3], lambda item: item == 4) is None


class TestGetMatchingFiles(object):
    def test_matching_files_as_paths(self):
        base_path = get_test_path('java')
        expected = sorted([Path('junit.pom.xml'), Path('junit-2.pom.xml'), Path('junit-no-ns.pom.xml')])

        assert sorted(get_matching_files(base_path, '*.xml')) == expected

    def test_matching_files_as_strings(self):
        base_path = get_test_path('java')
        expected = sorted(['junit.pom.xml', 'junit-2.pom.xml', 'junit-no-ns.pom.xml'])

        assert sorted(get_matching_files(base_path, '*.xml', to_str=True)) == expected


class TestRemoveDirectory(object):
    def test_remove_directory(self, tmpdir):
        temp_dir = Path(tmpdir)
        root = temp_dir / 'test'
        sub_dir = root / 'sub_dir'
        file_1 = root / 'root.txt'
        file_2 = sub_dir / 'file.txt'

        sub_dir.mkdir(parents=True)
        file_1.touch()
        file_2.touch()

        assert file_1.exists()
        assert file_2.exists()

        # Passing a file does nothing.
        remove_directory(file_2)

        assert file_1.exists()
        assert file_2.exists()

        # Removing works.
        remove_directory(root)

        assert not file_1.exists()
        assert not file_2.exists()
        assert not sub_dir.exists()
        assert not root.exists()


class TestOut(object):
    def test_simple_out(self):
        with FakeEcho.simple('test') as fe:
            out('test')
        assert fe.was_called()

    def test_out_with_kwargs(self):
        with FakeEcho.simple('test', fg='white') as fe:
            out('test', fg='white')
        assert fe.was_called()

    def test_out_quiet(self):
        with Options(quiet=True):
            with FakeEcho.simple('test') as fe:
                out('test')
        assert not fe.was_called()

    def test_out_ignore_quiet(self):
        with Options(quiet=True):
            with FakeEcho.simple('test') as fe:
                out('test', respect_quiet=False)
        assert fe.was_called()

        with FakeEcho.simple('test') as fe:
            out('test', respect_quiet=False)
        assert fe.was_called()

    def test_simple_verbose_out(self):
        with FakeEcho.simple('test') as fe:
            verbose_out('test')
        assert not fe.was_called()

    def test_verbose_out_verbose(self):
        with Options(verbose=1):
            with FakeEcho.simple('test', fg='white') as fe:
                verbose_out('test', fg='white')
            assert fe.was_called()

            with FakeEcho.simple('test', fg='green') as fe:
                verbose_out('test')
            assert fe.was_called()

    def test_labeled_out(self):
        with FakeEcho.simple('testing') as fe:
            labeled_out('testing')
        assert fe.was_called()

        with FakeEcho.simple('ERROR: testing') as fe:
            labeled_out('testing', label='ERROR')
        assert fe.was_called()

    def test_warn_out(self):
        with FakeEcho.simple('Warning: testing', fg='yellow') as fe:
            warn('testing')
        assert fe.was_called()

        with FakeEcho.simple('ERROR: testing', fg='yellow') as fe:
            warn('testing', label='ERROR')
        assert fe.was_called()

        with Options(quiet=True):
            with FakeEcho.simple('Warning: testing', fg='yellow') as fe:
                warn('testing')
            assert fe.was_called()


class TestEnd(object):
    def test_end(self):
        with FakeEcho.simple('ERROR: boom!', fg='bright_red') as fe:
            with pytest.raises(SystemExit):
                end('boom!')
        assert fe.was_called()


class TestCheckedRun(object):
    def test_verbose_output(self):
        cmd_line = ['ls', '-l']

        with Options(verbose=1):
            with FakeEcho.simple('Running: ls -l', fg='green') as fe:
                with FakeProcessContext(FakeProcess(cmd_line)):
                    checked_run(cmd_line, 'Testing')
            assert fe.was_called()

    def test_failure_output(self):
        cmd_line = ['ls', '-l']
        expected = [
            ExpectedEcho(r'ERROR: Testing failed with return code 2\.', fg='bright_red'),
            ExpectedEcho(r'ERROR: Command line: ls -l', fg='bright_red')
        ]

        with FakeEcho(expected) as fe:
            with FakeProcessContext(FakeProcess(cmd_line, rc=2)):
                with pytest.raises(SystemExit):
                    checked_run(cmd_line, 'Testing')
        assert fe.was_called()

    def test_allowed_rc(self):
        cmd_line = ['ls', '-l']

        with FakeEcho(None) as fe:
            with FakeProcessContext(FakeProcess(cmd_line, rc=2)):
                checked_run(cmd_line, 'Testing', allowed_rcs=[2])
        assert not fe.was_called()
