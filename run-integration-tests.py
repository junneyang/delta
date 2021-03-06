#!/usr/bin/env python

#
# Copyright (2020) The Delta Lake Project Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import sys
import fnmatch
import subprocess
from os import path
import random
import string
import tempfile


def run_scala_integration_tests(root_dir, version):
    print("##### Running Scala tests on version %s #####" % str(version))
    clear_artifact_cache()
    test_dir = path.join(root_dir, "examples", "scala")
    test_src_dir = path.join(test_dir, "src", "main", "scala", "example")
    test_classes = [f.replace(".scala", "") for f in os.listdir(test_src_dir)
                    if f.endswith(".scala") and not f.startswith("_")]
    with WorkingDirectory(test_dir):
        for test_class in test_classes:
            try:
                cmd = ["build/sbt", "runMain example.%s" % test_class]
                print("Running Scala tests in %s\n=====================" % test_class)
                print("Command: %s" % str(cmd))
                run_cmd(cmd, stream_output=True, env={"DELTA_VERSION": str(version)})
            except:
                print("Failed Scala tests in %s" % (test_class))
                raise


def run_python_integration_tests(root_dir, version):
    print("##### Running Python tests on version %s #####" % str(version))
    clear_artifact_cache()
    test_dir = path.join(root_dir, path.join("examples", "python"))
    test_files = [path.join(test_dir, f) for f in os.listdir(test_dir)
                  if path.isfile(path.join(test_dir, f)) and
                  f.endswith(".py") and not f.startswith("_")]
    python_root_dir = path.join(root_dir, "python")
    extra_class_path = path.join(python_root_dir, path.join("delta", "testing"))
    package = "io.delta:delta-core_2.11:" + version
    repo = 'https://dl.bintray.com/delta-io/delta'
    for test_file in test_files:
        try:
            cmd = ["spark-submit",
                   "--driver-class-path=%s" % extra_class_path,  # for less verbose logging
                   "--packages", package,
                   "--repositories", repo, test_file]
            print("Running Python tests in %s\n=============" % test_file)
            print("Command: %s" % str(cmd))
            run_cmd(cmd, stream_output=True)
        except:
            print("Failed Python tests in %s" % (test_file))
            raise


def clear_artifact_cache():
    print("Clearing Delta artifacts from ivy2 and mvn cache")
    run_cmd(["rm", "-rf", "~/.ivy2/cache/io.delta/"], stream_output=True)
    run_cmd(["rm", "-rf", "~/.m2/repository/io/delta/"], stream_output=True)


def run_cmd(cmd, throw_on_error=True, env=None, stream_output=False, **kwargs):
    cmd_env = os.environ.copy()
    if env:
        cmd_env.update(env)

    if stream_output:
        child = subprocess.Popen(cmd, env=cmd_env, **kwargs)
        exit_code = child.wait()
        if throw_on_error and exit_code != 0:
            raise Exception("Non-zero exitcode: %s" % (exit_code))
        return exit_code
    else:
        child = subprocess.Popen(
            cmd,
            env=cmd_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs)
        (stdout, stderr) = child.communicate()
        exit_code = child.wait()
        if throw_on_error and exit_code is not 0:
            raise Exception(
                "Non-zero exitcode: %s\n\nSTDOUT:\n%s\n\nSTDERR:%s" %
                (exit_code, stdout, stderr))
        return (exit_code, stdout, stderr)


# pylint: disable=too-few-public-methods
class WorkingDirectory(object):
    def __init__(self, working_directory):
        self.working_directory = working_directory
        self.old_workdir = os.getcwd()

    def __enter__(self):
        os.chdir(self.working_directory)

    def __exit__(self, tpe, value, traceback):
        os.chdir(self.old_workdir)


if __name__ == "__main__":
    """
        Script to run integration tests which are located in the examples directory.
        call this by running "python run-integration-tests.py"
        additionally the version can be provided as a command line argument.
        "
    """
    root_dir = path.dirname(path.dirname(__file__))
    # check if version is provided as an argument
    version = '0.0.0'
    if len(sys.argv) >= 2:
        version = sys.argv[1]

    # get the version of the package
    if version == '0.0.0':
        with open(path.join(root_dir, "version.sbt")) as fd:
            version = fd.readline().split('"')[1]

    run_scala_integration_tests(root_dir, version)
    run_python_integration_tests(root_dir, version)
