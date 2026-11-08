#!/usr/bin/env python3

import fnmatch
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


KANJI = "-kanji=jis"
# FONTS = ["-f", "haranoaji.map", "-f", "ptex-haranoaji.map"]
FONTS = ["-f", "ptex-haranoaji-04.map"]

BINARYFILES = ["*.pdf", "*.zip"]

# ドキュメントのタイプセット用のフォーマット名
TYPESET_FMT_NAME = "platex-build"
# テスト用のフォーマット名
TEST_FMT_NAME = "platex-test"

STRIP_CMD = ["platex-dev"]
PLATEX_CMD = ["platex-dev", "-progname=platex-dev"]
MAX_PRINT_LINE = 9999

DVIPDF_CMD = ["dvipdfmx", *FONTS]

# --------------------------------------------------------------------
# ユーティリティ関数
# --------------------------------------------------------------------


# コマンド実行
def run(*cmd, cwd=None, env=None):
    print("+", *cmd)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


ROOT = Path.cwd()


# ファイル削除
def rm(*patterns):
    for pattern in patterns:
        for p in ROOT.glob(str(pattern)):
            if p.is_file():
                p.unlink()


def makecleandir(path):
    path = Path(path)
    if path.is_dir:
        for p in path.iterdir():
            if p.is_file():
                p.unlink()
    else:
        os.makedirs(path)


# ファイル書き込み
def write(path, *contents):
    with open(path, "w", encoding="utf-8") as f:
        for content in contents:
            f.write(content)
            f.write("\n")


# タイムスタンプが古くなっているかチェック
def check_timestamp(target, *sources):
    target = Path(target)
    if not target.exists():
        return True
    target_time = target.stat().st_mtime
    for source in sources:
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(source)
        source_time = source.stat().st_mtime
        if target_time < source_time:
            return True
    return False


# フォーマットを作成
def fmt_latex(fmtname, cwd=None, env=None):
    work_dir = Path(cwd) if cwd is not None else Path()
    rm(work_dir / f"{fmtname}.fmt")
    run(
        *PLATEX_CMD,
        "-ini",
        "-etex",
        KANJI,
        "-halt-on-error",
        f"-jobname={fmtname}",
        "*platex.ini",
        cwd=cwd,
        env=env,
    )
    rm(work_dir / f"{fmtname}.log")


# --------------------------------------------------------------------
# strip
# --------------------------------------------------------------------


# docstrip実行
def run_strip(ins):
    run(*STRIP_CMD, KANJI, ins)


# stripメイン処理
def strip():
    rm(
        "platex.ltx",
        "plcore.ltx",
        "kinsoku.tex",
        "pldefs.ltx",
        "jy1mc.fd",
        "jy1gt.fd",
        "jt1mc.fd",
        "jt1gt.fd",
        "plext.sty",
        "ptrace.sty",
        "pfltrace.sty",
        "plexpl3.sty",
        "plexpl3.ltx",
    )
    run_strip("plfmt.ins")
    rm("plfmt.log")

    rm(
        "jarticle.cls",
        "jreport.cls",
        "jbook.cls",
        "jsize10.clo",
        "jsize11.clo",
        "jsize12.clo",
        "jbk10.clo",
        "jbk11.clo",
        "jbk12.clo",
        "tarticle.cls",
        "treport.cls",
        "tbook.cls",
        "tsize10.clo",
        "tsize11.clo",
        "tsize12.clo",
        "tbk10.clo",
        "tbk11.clo",
        "tbk12.clo",
    )
    run_strip("plcls.ins")
    rm("plcls.log")

    rm(
        "pl209.def",
        "oldpfont.sty",
        "jarticle.sty",
        "tarticle.sty",
        "jbook.sty",
        "tbook.sty",
        "jreport.sty",
        "treport.sty",
    )
    run_strip("pl209.ins")
    rm("pl209.log")

    rm("platexrelease.sty")
    run_strip("platexrelease.ins")
    rm("platexrelease.log")

    rm("jltxdoc.cls", "pldoc.tex", "Xins.ins")
    run_strip("pldocs.ins")
    rm("pldocs.log", "pldoc.tex", "Xins.ins")


# --------------------------------------------------------------------
# ドキュメントタイプセット
# --------------------------------------------------------------------


# ドキュメントタイプセット
def run_latex(tex, jobname=None):
    options = [
        f"-fmt={TYPESET_FMT_NAME}",
        KANJI,
        f"-cnf-line=max_print_line={MAX_PRINT_LINE}",
        "-halt-on-error",
    ]
    if jobname is not None:
        options += [f"-jobname={jobname}"]
    run(*PLATEX_CMD, *options, tex)


# latexの再実行が必要かチェック
def check_rerun(logname):
    RERUN_PATTERNS = [
        "Label(s) may have changed.",
        "Package rerunfilecheck Warning:",
        "Rerun to get ",
    ]
    log = Path(logname).read_text(encoding="utf-8", errors="replace")
    for pattern in RERUN_PATTERNS:
        if pattern in log:
            return True
    return False


# ドキュメントタイプセット（自動再実行）
def autorerun_latex(tex, jobname=None, max_run=3):
    logname = Path(tex).with_suffix(".log")
    if jobname is not None:
        logname = f"{jobname}.log"
    rerun = True
    run = 0
    while rerun and run < max_run:
        run += 1
        run_latex(tex, jobname)
        rerun = check_rerun(logname)
        if rerun:
            print("RERUN: Detect needs rerun in", logname)


# index用mendex実行
def run_index(name):
    run(
        "mendex",
        "-J",
        "-s",
        "gind.ist",
        "-d",
        "pldoc.dic",
        "-o",
        f"{name}.ind",
        f"{name}.idx",
    )


# glossary用mendex実行
def run_glossary(name):
    run(
        "mendex",
        "-J",
        "-f",
        "-s",
        "gglo.ist",
        "-o",
        f"{name}.gls",
        f"{name}.glo",
    )


# ドキュメントタイプセットメイン処理
def build_docs():
    fmt_latex(TYPESET_FMT_NAME)

    # Japanese documents

    rm("platex.cfg")

    run_latex("platex.dtx")
    run_glossary("platex")
    autorerun_latex("platex.dtx")
    rm(
        "platex.aux",
        "platex.log",
        "platex.hd",
        "platex.out",
        "platex.glo",
        "platex.gls",
        "platex.ilg",
    )

    autorerun_latex("platexrelease.dtx")
    rm(
        "platexrelease.aux",
        "platexrelease.log",
        "platexrelease.hd",
        "platexrelease.out",
    )

    rm("jltxdoc.cls", "pldoc.tex", "Xins.ins")
    run_strip("pldocs.ins")
    rm("pldoc.toc", "pldoc.idx", "pldoc.glo")
    write("ltxdoc.cfg")
    run_latex("pldoc.tex")
    run_index("pldoc")
    run_glossary("pldoc")
    write("ltxdoc.cfg", R"\includeonly{}")
    run_latex("pldoc.tex")
    write("ltxdoc.cfg")
    autorerun_latex("pldoc.tex")
    rm(
        "*.aux",
        "*.log",
        "pldoc.toc",
        "pldoc.hd",
        "pldoc.out",
        "pldoc.idx",
        "pldoc.ind",
        "pldoc.ilg",
        "pldoc.glo",
        "pldoc.gls",
        "pldoc.tex",
        "Xins.ins",
        "ltxdoc.cfg",
        "pldoc.dic",
    )

    autorerun_latex("exppl2e.sty")
    rm("exppl2e.aux", "exppl2e.log", "exppl2e.hd", "exppl2e.out")

    # English docments

    write("platex.cfg", R"\newif\ifJAPANESE")

    run_latex("platex.dtx", jobname="platex-en")
    run_glossary("platex-en")
    autorerun_latex("platex.dtx", jobname="platex-en")
    rm(
        "platex-en.aux",
        "platex-en.hd",
        "platex-en.out",
        "platex-en.log",
        "platex-en.glo",
        "platex-en.gls",
        "platex-en.ilg",
    )

    # rm("jltxdoc.cls", "pldoc.tex", "Xins.ins")
    # run_strip("pldocs.ins")
    # rm("pldoc.toc", "pldoc.idx", "pldoc.glo")
    # write("ltxdoc.cfg")
    # run_latex("pldoc.tex", jobname="pldoc-en")
    # run_index("pldoc-en")
    # run_glossary("pldoc-en")
    # write("ltxdoc.cfg", R"\includeonly{}")
    # run_latex("pldoc.tex", jobname="pldoc-en")
    # write("ltxdoc.cfg")
    # autorerun_latex("pldoc.tex", jobname="pldoc-en")
    # rm(
    #     "*.aux",
    #     "*.log",
    #     "pldoc-en.toc",
    #     "pldoc-en.hd",
    #     "pldoc-en.out",
    #     "pldoc-en.idx",
    #     "pldoc-en.ind",
    #     "pldoc-en.ilg",
    #     "pldoc-en.glo",
    #     "pldoc-en.gls",
    #     "pldoc.tex",
    #     "Xins.ins",
    #     "ltxdoc.cfg",
    #     "pldoc.dic",
    # )

    rm("platex.cfg")
    rm(f"{TYPESET_FMT_NAME}.fmt")


# --------------------------------------------------------------------
# PDF作成
# --------------------------------------------------------------------


# dvipdfmx実行
def run_dvipdf(dvi, cwd=None):
    run(*DVIPDF_CMD, dvi, cwd=cwd)


# PDF作成メイン処理
def build_pdfs():
    run_dvipdf("platex.dvi")
    run_dvipdf("platexrelease.dvi")
    run_dvipdf("pldoc.dvi")
    run_dvipdf("exppl2e.dvi")

    run_dvipdf("platex-en.dvi")
    # run_dvipdf("pldoc-en.dvi")


# --------------------------------------------------------------------
# test
# --------------------------------------------------------------------


# エラーが起こらないことを確認するテスト用
def test_noerror(tex, cwd, env):
    run(
        *PLATEX_CMD,
        f"-fmt={TEST_FMT_NAME}",
        "-kanji=utf8",
        "-halt-on-error",
        tex,
        cwd=cwd,
        env=env,
    )


# PDFを確認するテスト用
def test_genpdf(tex, cwd, env):
    run(
        *PLATEX_CMD,
        f"-fmt={TEST_FMT_NAME}",
        "-kanji=utf8",
        "-halt-on-error",
        tex,
        cwd=cwd,
        env=env,
    )
    run_dvipdf(
        Path(tex).with_suffix(".dvi").name,
        cwd=cwd,
    )


def test(tests):
    test_dir = Path("build/test")
    makecleandir(test_dir)

    test_env = {"TEXINPUTS": ".;../..;../../tests;"}

    # テスト用フォーマットを作成
    fmt_latex(TEST_FMT_NAME, cwd=test_dir, env={"TEXINPUTS": ".;../..;"})

    TESTS = {
        # エラーが起こらないことを確認
        "atbegindvi_tate": test_noerror,
        "decfontenc_utf8_ly1": test_noerror,
        "decfontenc_utf8x": test_noerror,
        "footnote_vert": test_noerror,
        "plext_arraybox": test_noerror,
        "plext_multicolumn": test_noerror,
        "setref_math": test_noerror,
        #
        "plext_tabular_yoko": test_genpdf,
        "plext_tabular_tate": test_genpdf,
        "plext_parbox_yoko": test_genpdf,
        "plext_parbox_tate": test_genpdf,
    }

    if tests:
        for test in tests:
            test_func = TESTS[test] if test in TESTS else test_genpdf
            test_func(test, cwd=test_dir, env=test_env)
    else:
        for test, test_func in TESTS.items():
            test_func(test, cwd=test_dir, env=test_env)


# --------------------------------------------------------------------
# install
# --------------------------------------------------------------------


def get_texmfhome():
    result = subprocess.run(
        ["kpsewhich", "-var-value=TEXMFHOME"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,  # 標準エラーは無視
        check=True,  # 失敗したら例外を投げる
        encoding="utf-8",
        errors="replace",
    )
    value = result.stdout.strip()
    if len(value) == 0:
        raise Exception("TEXMFHOME not found")
    return value


def check_binaryfile(name):
    for pattern in BINARYFILES:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def copy_lf(src, dst):
    data = Path(src).read_bytes()
    if b"\0" in data:
        raise RuntimeError(f"NUL byte found in {src}.")
    Path(dst).write_bytes(data.replace(b"\r\n", b"\n"))


def install_files(target_dir, *patterns):
    target_dir = Path(target_dir)
    os.makedirs(target_dir, exist_ok=True)
    for pattern in patterns:
        for p in ROOT.glob(pattern):
            if p.is_file():
                # print("install", p.name, "to", target_dir)
                if check_binaryfile(p.name):
                    shutil.copyfile(p, target_dir / p.name)
                else:
                    copy_lf(p, target_dir / p.name)


def install(is_dev=False, texmf=None):
    if texmf is None:
        texmf = Path(get_texmfhome())

    fmtname = "platex" if not is_dev else "platex-dev"

    install_files(texmf / "doc" / fmtname / "base", "LICENSE", "README.md", "*.pdf")
    install_files(
        texmf / "source" / fmtname / "base",
        "Makefile",
        "plnews*.tex",
        "*.dtx",
        "*.ins",
    )
    install_files(
        texmf / "tex" / fmtname / "base",
        "kinsoku.tex",
        "*.clo",
        "*.cls",
        "*.def",
        "*.fd",
        "*.ltx",
        "*.sty",
    )
    install_files(texmf / "tex" / fmtname / "config", "platex.ini")


def uninstall(is_dev=False):
    texmf = Path(get_texmfhome())

    fmtname = "platex" if not is_dev else "platex-dev"

    shutil.rmtree(texmf / "doc" / fmtname / "base")
    shutil.rmtree(texmf / "source" / fmtname / "base")
    shutil.rmtree(texmf / "tex" / fmtname / "base")
    shutil.rmtree(texmf / "tex" / fmtname / "config")


# --------------------------------------------------------------------
# release processing
# --------------------------------------------------------------------


def run_git(*args):
    return subprocess.run(
        ["git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,  # 標準エラーは無視
        check=True,  # 失敗したら例外を投げる
        encoding="utf-8",
        errors="replace",
    ).stdout.strip()


def has_uncommitted_changes():
    return bool(run_git("status", "--porcelain"))


def get_head_tag():
    out = run_git("tag", "--points-at", "HEAD")
    tags = [line.strip() for line in out.splitlines() if line.strip()]

    if not tags:
        raise RuntimeError("Current commit is not tagged.")
    if len(tags) > 1:
        raise RuntimeError(f"Current commit has multiple tags: {', '.join(tags)}.")

    return tags[0]


def rewrite_releasedate(path, date):
    data = Path(path).read_bytes()
    data = data.replace(b"$RELEASEDATE", str(date).encode("ascii"))
    Path(path).write_bytes(data)


def create_zip(archive, base_dir, *files):
    if not files:
        files = ["."]
    subprocess.run(
        ["zip", "-r", str(Path(archive).resolve()), *files],
        check=True,  # 失敗したら例外を投げる
        cwd=base_dir,
    )


def create_archive(is_dev=False, is_test=False):
    if is_test:
        date = datetime.now().strftime("%Y-%m-%d")
        sha = run_git("rev-parse", "--short=8", "HEAD")
        tag = f"TEST-{date}-{sha}"
        if has_uncommitted_changes():
            tag += "-dirty"
    else:
        if has_uncommitted_changes():
            raise RuntimeError("Repository contains uncommitted changes.")
        tag = get_head_tag()

    pkgname = "platex" if not is_dev else "platex-dev"

    tds_name = f"{pkgname}.tds.zip"
    ctan_name = f"{pkgname}.zip"
    rm(ctan_name)

    work_dir = Path("build", "distrib")
    ctan_dir = work_dir / "ctan"
    tds_dir = work_dir / "tds"

    if work_dir.exists():
        shutil.rmtree(work_dir)

    os.makedirs(ctan_dir / pkgname, exist_ok=True)
    os.makedirs(tds_dir, exist_ok=True)

    # TDS

    install(texmf=tds_dir)
    rewrite_releasedate(tds_dir / "doc" / pkgname / "base" / "README.md", tag)

    create_zip(ctan_dir / tds_name, tds_dir)

    # CTAN

    install_files(
        ctan_dir / pkgname,
        "LICENSE",
        "Makefile",
        "README.md",
        "exppl2e.sty",
        "platex.ini",
        "plnews.cls",
        "plnews*.tex",
        "*.dtx",
        "*.ins",
        "*.pdf",
    )
    rewrite_releasedate(ctan_dir / pkgname / "README.md", tag)

    create_zip(ctan_name, ctan_dir, pkgname, tds_name)


# --------------------------------------------------------------------
# clean
# --------------------------------------------------------------------


def clean():
    shutil.rmtree("build", ignore_errors=True)
    rm(
        "*.dvi",
        "*.fmt",
        "*.aux",
        "*.log",
        "*.hd",
        "*.out",
        "*.idx",
        "*.ind",
        "*.ilg",
        "*.glo",
        "*.gls",
    )


# --------------------------------------------------------------------
# main
# --------------------------------------------------------------------


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "default"

    if cmd == "all":
        strip()
        build_docs()
        build_pdfs()
    elif cmd == "default":
        strip()
        build_docs()
    elif cmd == "strip":
        strip()
    elif cmd == "test":
        strip()
        test(sys.argv[2:])
    elif cmd == "install":
        uninstall()
        install()
    elif cmd == "uninstall":
        uninstall()
    elif cmd == "install-dev":
        uninstall(is_dev=True)
        install(is_dev=True)
    elif cmd == "uninstall-dev":
        uninstall(is_dev=True)
    elif cmd == "archive":
        create_archive()
    elif cmd == "archive-test":
        create_archive(is_test=True)
    elif cmd == "clean":
        clean()
    else:
        raise Exception("Unknown cmd")


if __name__ == "__main__":
    main()
