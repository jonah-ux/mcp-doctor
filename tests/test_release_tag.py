import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "check_release_tag", Path(__file__).parents[1] / "scripts/check_release_tag.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTagTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.repo = Path(self.directory.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Release Test")
        self.git("config", "user.email", "release-test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "tag.gpgsign", "false")
        (self.repo / "pyproject.toml").write_text('[project]\nversion = "0.2.0"\n')
        self.git("add", "pyproject.toml")
        self.git("commit", "-qm", "fixture")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True)

    def test_annotated_matching_tag_passes(self):
        self.git("tag", "-a", "v0.2.0", "-m", "release")
        release.validate(self.repo, "v0.2.0")

    def test_lightweight_tag_refused(self):
        self.git("tag", "v0.2.0")
        with self.assertRaisesRegex(ValueError, "annotated"):
            release.validate(self.repo, "v0.2.0")

    def test_wrong_version_refused(self):
        with self.assertRaisesRegex(ValueError, "project.version"):
            release.validate(self.repo, "v0.3.0")

    def test_malformed_tags_refused(self):
        for tag in ("v0.2.0-extra", "v0oops.2.0", "v00.2.0", "0.2.0", "v0.2.0.1"):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                release.validate(self.repo, tag)

    def test_tag_at_old_head_refused(self):
        self.git("tag", "-a", "v0.2.0", "-m", "release")
        self.git("commit", "--allow-empty", "-qm", "next")
        with self.assertRaisesRegex(ValueError, "HEAD"):
            release.validate(self.repo, "v0.2.0")


if __name__ == "__main__":
    unittest.main()
