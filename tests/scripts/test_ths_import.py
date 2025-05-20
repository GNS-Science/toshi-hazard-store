import pytest  # noqa
from click.testing import CliRunner

from toshi_hazard_store.scripts import ths_import  # module reference for patching

# from nzssdt_2023.scripts.pipeline_cli import cli
# from nzssdt_2023.versioning import VersionInfo


def test_cli_help():
    runner = CliRunner()
    cmdline = ["--help"]
    result = runner.invoke(ths_import.main, cmdline)
    assert result.exit_code == 0
    assert "Usage" in result.output

    # print(result.output)
    # assert 0


def test_cli_producers_help():
    runner = CliRunner()
    cmdline = ["producers", "--help"]
    result = runner.invoke(ths_import.main, cmdline)
    assert result.exit_code == 0
    assert "Usage" in result.output


@pytest.mark.parametrize("options", [None, "--verbose", "-v"])
def test_cli_rlzs_help(options):
    runner = CliRunner()
    cmdline = ["extract", "--help"]
    if options:
        cmdline += options.split(" ")
    result = runner.invoke(ths_import.main, cmdline)
    assert result.exit_code == 0
    assert "Usage" in result.output


@pytest.mark.parametrize(
    "options",
    [
        None,
    ],
)
def test_cli_store_hazard_help(options):
    runner = CliRunner()
    cmdline = ["store-hazard", "--help"]
    if options:
        cmdline += options.split(" ")
    result = runner.invoke(ths_import.main, cmdline)
    assert result.exit_code == 0
    assert "Usage" in result.output


### EXAMPLE from TS1170.SDP
#
# @pytest.mark.parametrize("options", [None, "--verbose"])
# def test_publish(mocker, options):
#     version_manager = version_cli.version_manager

#     # patch the underlying functions
#     vi_og = VersionInfo("MY_NEW_VER", "NSHM_v99")
#     vi_new = VersionInfo(
#         "MY_NEW_ONE", "NSHM_v00", description="Read all about the new one"
#     )

#     mocked_vi_collect = mocker.patch.object(
#         VersionInfo, "collect_manifest", return_value=[]
#     )
#     mocked_read_version_list = mocker.patch.object(
#         version_manager, "read_version_list", return_value={vi_og.version_id: vi_og}
#     )
#     mocked_write_version_list = mocker.patch.object(
#         version_manager, "write_version_list", return_value={vi_new.version_id: vi_new}
#     )

#     runner = CliRunner()

#     cmdline = ["06-publish", "MY_NEW_ONE", "NSHM_v00", "Read all about the new one"]
#     if options:
#         cmdline += options.split(" ")
#     result = runner.invoke(cli, cmdline)

#     print(result.output)
#     assert result.exit_code == 0

#     mocked_read_version_list.assert_called_once()
#     mocked_vi_collect.assert_called_once()
#     mocked_write_version_list.assert_called_once_with([vi_og, vi_new])

#     print(result.output)

#     if options and "--verbose" in options:
#         assert vi_new.version_id in result.output
#         assert vi_new.nzshm_model_version in result.output
#         assert vi_new.description in result.output

#     if options and "--verbose" in options and "--merge" not in options:
#         assert "Wrote new version" in result.output
