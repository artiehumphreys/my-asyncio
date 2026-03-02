from setuptools import setup, Extension

module = Extension(
    "_c_event_loop",
    sources=[
        "src/_c_event_loop_module.c",
        "src/event_loop.c",
        "src/heap.c",
    ],
    include_dirs=["src"],
    extra_compile_args=["-std=c17", "-Wall", "-Wextra"],
)

setup(
    name="my-asyncio",
    version="0.1.0",
    ext_modules=[module],
)
