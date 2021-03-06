from builder.schema import BooleanSchema, ObjectSchema, StringSchema
from builder.schema_validator import SchemaValidator
from ..models import Task, Language
from builder.utils import end

from .java import JavaConfiguration, get_javac_version, java_clean, java_test, java_version, PackageConfiguration
from .version_check import check_dependency_versions
from .compile import java_compile
from .doc import java_doc
from .package import java_package
from .resolver import resolve, project_to_lib_dir

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
        tests_resources=StringSchema().min_length(1).default('test_resources'),
        tests_target=StringSchema().min_length(1).default('tests/classes'),
        dist=StringSchema().min_length(1).default('dist'),
        app_target=StringSchema().min_length(1).default('app'),
        lib_target=StringSchema().min_length(1).default('lib')
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
        Task('clean', java_clean, help_text='Removes build artifacts from other Java tasks.'),
        Task('compile', java_compile, help_text='Compiles Java source code for the project.'),
        Task('test', java_test, require=['compile'], help_text='Tests the compiled Java code for the project.'),
        Task('doc', java_doc, help_text='Produces javadoc documentation from the Java source in the project.'),
        Task('package', java_package, require=['test'], configuration_class=PackageConfiguration,
             configuration_schema=SchemaValidator(schema=_package_configuration_schema),
             help_text='Packages artifacts for the project.'),
        Task('build', None, require=['clean', 'test', 'doc', 'package'], help_text='Build everything in the project.'),
        Task('check-versions', check_dependency_versions,
             help_text='Verifies the version of each dependency in the project.')
    ]
    language.resolver = resolve
    language.project_to_path = project_to_lib_dir


if java_version is None:
    end('The Java Development Kit (JDK) is not available on the path.')
