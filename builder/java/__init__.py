from builder.schema import BooleanSchema, ObjectSchema, StringSchema
from builder.schema_validator import SchemaValidator
from .sync_ij import sync_dependencies_to_ij
from ..models import Task, Language
from builder.utils import end

from .java import JavaConfiguration, get_javac_version, java_clean, java_version, PackageConfiguration, \
    TestingConfiguration
from .init import init_java_project
from .version_check import check_dependency_versions
from .compile import java_compile
from .doc import java_doc
from .package import java_package
from .resolver import resolve, project_to_dist_dir
from .test import compile_tests, run_tests

_configuration_schema = ObjectSchema()\
    .properties(
        type=StringSchema().enum('library', 'application').default('library'),
        source=StringSchema().min_length(1).default('src'),
        build=StringSchema().min_length(1).default('build'),
        code_source=StringSchema().min_length(1).default('code'),
        code_resources=StringSchema().min_length(1).default('resources'),
        code_target=StringSchema().min_length(1).default('code/classes'),
        code_doc=StringSchema().min_length(1).default('code/javadoc'),
        tests_source=StringSchema().min_length(1).default('tests'),
        test_resources=StringSchema().min_length(1).default('test_resources'),
        tests_target=StringSchema().min_length(1).default('tests/classes'),
        dist=StringSchema().min_length(1).default('dist'),
        app_target=StringSchema().min_length(1).default('app'),
        lib_target=StringSchema().min_length(1).default('lib')
    )\
    .additional_properties(False)

_test_configuration_schema = ObjectSchema()\
    .properties(
        test_executor=StringSchema().min_length(1),
        coverage_agent=StringSchema().min_length(1),
        coverage_reporter=StringSchema().min_length(1),
        test_reports=StringSchema(),
        coverage_reports=StringSchema()
    )\
    .additional_properties(False)

_package_configuration_schema = ObjectSchema()\
    .properties(
        entry_point=StringSchema().min_length(1),
        sources=BooleanSchema(),
        doc=BooleanSchema()
    )\
    .additional_properties(False)

configuration_class = JavaConfiguration
configuration_schema = SchemaValidator(schema=_configuration_schema)


def define_language(language: Language):
    language.configuration_class = configuration_class
    language.configuration_schema = configuration_schema
    language.tasks = [
        Task('init', init_java_project, help_text='Initializes things for a new project, including IntelliJ files.'),
        Task('clean', java_clean, help_text='Removes build artifacts from other Java tasks.'),
        Task('compile', java_compile, help_text='Compiles Java source code for the project.'),
        Task('compile-tests', compile_tests, require=['compile'], help_text='Compiles any unit tests for the project.'),
        Task('test', run_tests, require=['compile-tests'], configuration_class=TestingConfiguration,
             configuration_schema=SchemaValidator(schema=_test_configuration_schema),
             help_text='Executes any unit tests for the project.'),
        Task('doc', java_doc, help_text='Produces javadoc documentation from the Java source in the project.'),
        Task('package', java_package, require=['test'], configuration_class=PackageConfiguration,
             configuration_schema=SchemaValidator(schema=_package_configuration_schema),
             help_text='Packages artifacts for the project.'),
        Task('build', None, require=['clean', 'test', 'doc', 'package'], help_text='Build everything in the project.'),
        Task('check-versions', check_dependency_versions,
             help_text='Verifies the version of each dependency in the project.'),
        Task('sync-ij', sync_dependencies_to_ij,
             help_text='Updates IntelliJ project files to match dependencies in project.yaml.')
    ]
    language.resolver = resolve
    language.project_as_dist_path = project_to_dist_dir


if java_version is None:
    end('The Java Development Kit (JDK) is not available on the path.')
