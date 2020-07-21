from builder.dependencies import dependency_resolver, ResolverData
from builder.schema import BooleanSchema, ObjectSchema, StringSchema
from builder.schema_validator import SchemaValidator
from builder.task_module import Task
from builder.utils import end

from .java import JavaConfiguration, get_javac_version, java_clean, java_test, java_doc, java_version, \
    PackageConfiguration
from .compile import java_compile
from .package import java_package
from .maven import maven_resolver

_configuration_schema = ObjectSchema()\
    .properties(
        type=StringSchema().enum('library', 'application').default('library'),
        source=StringSchema().min_length(1).default('src'),
        build=StringSchema().min_length(1).default('build'),
        code_source=StringSchema().min_length(1).default('code'),
        code_resources=StringSchema().min_length(1).default('resources'),
        code_target=StringSchema().min_length(1).default('code/classes'),
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
        sign_with=StringSchema().min_length(1)
    )\
    .additional_properties(False)

configuration_class = JavaConfiguration
configuration_schema = SchemaValidator(schema=_configuration_schema)

dependency_resolver.register_resolver('maven', ResolverData(function=maven_resolver))
dependency_resolver.register_name_format('java', '{name}-{version}.jar')

tasks = [
    Task('clean', java_clean, help_text='Removes build artifacts from other Java tasks.'),
    Task('compile', java_compile, help_text='Compiles Java source code for the project.'),
    Task('test', java_test, require=['compile'], help_text='Tests the compiled Java code for the project.'),
    Task('doc', java_doc, help_text='Produces javadoc documentation from the Java source in the project.'),
    Task('package', java_package, require=['test'], configuration_class=PackageConfiguration,
         configuration_schema=SchemaValidator(schema=_package_configuration_schema),
         help_text='Packages artifacts for the project.'),
    Task('build', None, require=['clean', 'test', 'doc', 'package'], help_text='Build everything in the project.')
]

if java_version is None:
    end('The Java Development Kit (JDK) is not available on the path.')
