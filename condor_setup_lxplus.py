#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

"""
How to run (Python 2.7 / CMSSW_10_6_20):
  python condor_setup_lxplus.py --input_file <your_list.txt> --year 2022preEE --isMC

Input file example (under input_data_Files/):
  DYGto2LG_10to50 /DYGto2LG-1Jets_MLL-50_PTG-10to50_TuneCP5_13.6TeV_amcatnloFXFX-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM
  ALP_M5          /eos/home-p/pelai/HZa/private_mc/signal/run3/HZaTo2l2g_M5_NanoAODv12/
"""

import argparse
import os
import sys

# Utils in your repo
sys.path.append("Utils/.")
from color_style import style  # noqa: E402

# ===== Helpers for EOS listing (Py2) =====
def _which(cmd):
    try:
        from distutils.spawn import find_executable
        return find_executable(cmd)
    except Exception:
        return None

def _pick_xrootd_host_for_path(eos_abs_path, default_host):
    """
    Auto-pick XRootD host based on /eos path prefix:
      /eos/home-<x>/...  -> root://eoshome-<x>.cern.ch/
      /eos/user/...      -> root://eosuser.cern.ch/
    Otherwise, use default_host.
    """
    if eos_abs_path.startswith("/eos/home-") and len(eos_abs_path) >= len("/eos/home-x/"):
        letter = eos_abs_path[len("/eos/home-")]
        try:
            if letter.isalpha():
                return "root://eoshome-" + letter + ".cern.ch/"
        except Exception:
            pass
    if eos_abs_path.startswith("/eos/user/"):
        return "root://eosuser.cern.ch/"
    return default_host

def _list_eos_with_eoscli(eos_bin, path_abs):
    cmd = eos_bin + ' find -name "*.root" ' + path_abs
    try:
        out = os.popen(cmd).read()
        return [x for x in out.split() if x.endswith(".root")]
    except Exception:
        return []

def _list_eos_with_xrdfs(xrootd_host_url, path_abs):
    xrdfs = _which("xrdfs")
    if not xrdfs:
        return []
    host = xrootd_host_url.replace("root://", "").rstrip("/")
    cmd = xrdfs + " " + host + " ls -R " + path_abs
    try:
        out = os.popen(cmd).read()
        return [line.strip() for line in out.splitlines() if line.strip().endswith(".root")]
    except Exception:
        return []

def _list_eos_with_oswalk(path_abs):
    found = []
    for dirpath, dirnames, filenames in os.walk(path_abs):
        for fn in filenames:
            if fn.endswith(".root"):
                found.append(os.path.join(dirpath, fn))
    return found

def list_local_eos_root_files(path_abs, default_host):
    """
    Return (files_abs_list, xrootd_host_url_used).
    Strategy: EOS CLI (/usr/bin/eos -> eos -> /cvmfs/.../eos) -> xrdfs -> os.walk
    """
    host = _pick_xrootd_host_for_path(path_abs, default_host)

    # 1) eos CLI attempts
    tried_bins = ("/usr/bin/eos", "eos", "/cvmfs/eos.cern.ch/bin/eos")
    for eos_bin in tried_bins:
        if _which(eos_bin) or os.path.exists(eos_bin):
            files = _list_eos_with_eoscli(eos_bin, path_abs)
            if files:
                return files, host

    # 2) xrdfs fallback
    files = _list_eos_with_xrdfs(host, path_abs)
    if files:
        return files, host

    # 3) os.walk last resort
    files = _list_eos_with_oswalk(path_abs)
    return files, host


def main(args):
    # ========= argparse variables =========
    submission_name = args.submission_name
    use_custom_eos = args.use_custom_eos
    use_custom_eos_cmd = args.use_custom_eos_cmd
    input_file_name = args.input_file
    skimmed_output_path = args.eos_output_path or "/eos/home-p/pelai/HZa/mc_NATool"
    year = str(args.year)
    isMC = args.isMC
    condor_log_path = args.condor_log_path
    condor_queue = args.condor_queue
    DontCreateTarFile = args.DontCreateTarFile
    post_proc_to_run = args.post_proc
    Transfer_Input_Files = args.transfer_input_files
    eos_xrootd_host = args.eos_xrootd_host.rstrip("/") + "/"

    # 固定命名：submit_condor_jobs_HZa_<submission_name>
    condor_file_name = "submit_condor_jobs_HZa_" + submission_name

    # ========= 获取环境信息 =========
    TOP_LEVEL_DIR_NAME = os.path.basename(os.getcwd())

    import infoCreaterGit
    try:
        summary = raw_input("\n\nWrite summary for current job submission: ")
    except NameError:
        summary = input("\n\nWrite summary for current job submission: ")
    infoLogFiles = infoCreaterGit.BasicInfoCreater("summary.dat", summary)
    infoLogFiles.generate_git_patch_and_log()

    cmsswDirPath = os.environ.get("CMSSW_BASE", "")
    if not cmsswDirPath:
        print("ERROR: CMSSW_BASE not found in environment.")
        sys.exit(1)
    CMSSWRel = cmsswDirPath.split("/")[-1]

    # ========= 创建日志与输出目录 =========
    import fileshelper
    dirsToCreate = fileshelper.FileHelper(
        (condor_log_path + "/condor_logs/" + submission_name).replace("//", "/"),
        skimmed_output_path,
    )
    output_log_path = dirsToCreate.create_log_dir_with_date()
    storeDir = dirsToCreate.create_store_area(skimmed_output_path)
    _ = dirsToCreate.dir_name  # keep for compatibility

    # ========= 打包 CMSSW（可选） =========
    if not DontCreateTarFile:
        os.system("rm -f CMSSW*.tgz")

    import makeTarFile
    print("copying the " + CMSSWRel + ".tgz file to eos path: " + storeDir + "\n")
    if not DontCreateTarFile:
        if not os.path.exists(storeDir):
            os.makedirs(storeDir)
        tgz_path = os.path.join(storeDir, CMSSWRel + ".tgz")
        if os.path.exists(tgz_path):
            os.system("rm " + tgz_path)
        makeTarFile.make_tarfile(cmsswDirPath, tgz_path)
    else:
        print("Skipping tar file creation")

    # ========= 生成 JDL =========
    command = "python " + post_proc_to_run + " -y " + year + " -m " + str(isMC)

    input_path = os.path.join("input_data_Files", input_file_name)
    if not os.path.isfile(input_path):
        print("ERROR: input file not found: " + input_path)
        sys.exit(1)

    outjdl_file = open(condor_file_name + ".jdl", "w")
    outjdl_file.write('+JobFlavour   = "' + condor_queue + '"\n')
    outjdl_file.write("Executable = " + condor_file_name + ".sh\n")
    outjdl_file.write("Universe = vanilla\n")
    outjdl_file.write("Notification = ERROR\n")
    outjdl_file.write("Should_Transfer_Files = YES\n")
    outjdl_file.write("WhenToTransferOutput = ON_EXIT\n")
    outjdl_file.write("Transfer_Input_Files = " + Transfer_Input_Files + ", " + post_proc_to_run + "\n")
    outjdl_file.write("x509userproxy = $ENV(X509_USER_PROXY)\n")
    # 下面两行可能互相冲突（视站点而定），如有投递问题，可注释掉其中之一
    outjdl_file.write('requirements = TARGET.OpSysAndVer =?= "AlmaLinux9"\n')
    outjdl_file.write('MY.WantOS = "el7"\n')

    count_jobs = 0
    with open(input_path) as in_file:
        for raw in in_file:
            line = raw.strip()
            if (not line) or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                print("Skip malformed line: " + line)
                continue

            tag = parts[0]                   # e.g. DYGto2LG_10to50, ALP_M5
            second_field = parts[1].strip()  # DAS dataset or /eos/... local path

            print(style.RED + "=" * 51 + style.RESET)
            print("==> tag = " + tag)
            print("==> second_field = " + second_field)

            output_string = tag + "_" + year
            output_path = os.path.join(skimmed_output_path, output_string)
            print("==> output_path = " + output_path)
            os.system("mkdir -p " + output_path)
            infoLogFiles.send_git_log_and_patch_to_eos(output_path)

            # ==== 分支 A：本地 EOS 目录（使用 POSIX 路径 /eos/...，不拼 root://）====
            if second_field.startswith("/eos/"):
                local_files, chosen_host = list_local_eos_root_files(second_field, eos_xrootd_host)

                print("Chosen XRootD host for listing: " + chosen_host)
                print("Number of files (local EOS): " + str(len(local_files)))

                for root_file in local_files:
                    # 确保是绝对路径
                    if not root_file.startswith("/"):
                        root_file = "/" + root_file
                    # 直接使用 POSIX 路径（不转成 root://）
                    in_url = root_file
                    sample_name_for_logs = tag

                    outjdl_file.write("Output = " + output_log_path + "/" + sample_name_for_logs + "_$(Process).stdout\n")
                    outjdl_file.write("Error  = " + output_log_path + "/" + sample_name_for_logs + "_$(Process).err\n")
                    outjdl_file.write("Log    = " + output_log_path + "/" + sample_name_for_logs + "_$(Process).log\n")

                    dest_name = os.path.basename(root_file).replace(".root", "skimmed.root")
                    out_arg = in_url + " " + skimmed_output_path + "/" + output_string + "/" + dest_name + "  " + skimmed_output_path
                    outjdl_file.write("Arguments = " + out_arg + "\n")
                    outjdl_file.write("Queue \n")
                    count_jobs += 1

                print("Number of jobs (till now): " + str(count_jobs))
                continue

            # ==== 分支 B：DAS 数据集（保持 root://cms-xrd-global.cern.ch）====
            SampleDASName = second_field
            sample_name = tag
            try:
                sample_name = SampleDASName.split("/")[1]
            except Exception:
                pass

            if use_custom_eos:
                xrd_redirector = "root://cms-xrd-global.cern.ch/"
                out = os.popen(use_custom_eos_cmd + SampleDASName.strip()).read()
            else:
                xrd_redirector = "root://cms-xrd-global.cern.ch/"
                out = os.popen('dasgoclient --query="file dataset=' + SampleDASName.strip() + '"').read()

            das_files = [x for x in out.split() if x.endswith(".root")]
            print("Number of files (DAS): " + str(len(das_files)))

            for root_file in das_files:
                # 确保 /store/... 为绝对路径
                if not root_file.startswith("/"):
                    root_file = "/" + root_file
                in_url = xrd_redirector.rstrip("/") + root_file

                outjdl_file.write("Output = " + output_log_path + "/" + sample_name + "_$(Process).stdout\n")
                outjdl_file.write("Error  = " + output_log_path + "/" + sample_name + "_$(Process).err\n")
                outjdl_file.write("Log    = " + output_log_path + "/" + sample_name + "_$(Process).log\n")
                dest_name = os.path.basename(root_file).replace(".root", "skimmed.root")
                out_arg = in_url + " " + skimmed_output_path + "/" + output_string + "/" + dest_name + "  " + skimmed_output_path
                outjdl_file.write("Arguments = " + out_arg + "\n")
                outjdl_file.write("Queue \n")
                count_jobs += 1

            print("Number of jobs (till now): " + str(count_jobs))

    outjdl_file.close()

    # ========= 生成执行脚本 =========
    outScript = open(condor_file_name + ".sh", "w")
    outScript.write("#!/bin/bash\n")
    outScript.write('echo "Starting job on " `date`\n')
    outScript.write('echo "Running on: `uname -a`"\n')
    outScript.write('echo "System software: `cat /etc/redhat-release`"\n')
    outScript.write("source /cvmfs/cms.cern.ch/cmsset_default.sh\n")
    outScript.write('echo "copy cmssw tar file from store area"\n')
    outScript.write("cp -s ${3}/" + CMSSWRel + ".tgz .\n")
    outScript.write("tar -xf " + CMSSWRel + ".tgz\n")
    outScript.write("rm " + CMSSWRel + ".tgz\n")
    outScript.write("cd " + CMSSWRel + "/src/PhysicsTools/NanoAODTools/python/postprocessing/analysis/" + TOP_LEVEL_DIR_NAME + "/\n")
    outScript.write("rm -f *.root\n")
    outScript.write("scramv1 b ProjectRename\n")
    outScript.write("eval `scram runtime -sh`\n")
    outScript.write('echo "========================================="\n')
    outScript.write('echo "cat post_proc.py"\n')
    outScript.write('echo "..."\n')
    outScript.write("cat post_proc.py\n")
    outScript.write('echo "..."\n')
    outScript.write('echo "========================================="\n')
    outScript.write(command + " --entriesToRun 0 --inputFile ${1}\n")
    outScript.write('echo "====> List root files : "\n')
    outScript.write("ls -alh *.root\n")
    outScript.write('echo "====> copying *.root file to stores area..."\n')
    outScript.write("if [ -f skimmed_nano_mc.root ]; then cp skimmed_nano_mc.root ${2}; fi\n")
    outScript.write("rm -f *.root\n")
    outScript.write("cd ${_CONDOR_SCRATCH_DIR}\n")
    outScript.write("rm -rf " + CMSSWRel + "\n")
    outScript.close()
    os.system("chmod 777 " + condor_file_name + ".sh")

    # ========= 提示 =========
    print("\n#===> Set Proxy Using:")
    print("voms-proxy-init --voms cms --valid 168:00")
    print("\n# It is assumed that the proxy is created in file: /tmp/x509up_u175325. Update this in below two lines:")
    print("cp /tmp/x509up_u175325 ~/")
    print("export X509_USER_PROXY=~/x509up_u175325")
    print("\n# Submit jobs:")
    print("condor_submit " + condor_file_name + ".jdl")


# ---------- argparse ----------
class PreserveWhitespaceFormatter(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Condor Job Submission",
        formatter_class=PreserveWhitespaceFormatter,
    )
    parser.add_argument("--submission_name", default="SkimNanoAOD", help="A tag for this submission.")
    parser.add_argument("--use_custom_eos", default=False, action="store_true", help="Use custom EOS command to list files.")
    parser.add_argument("--DontCreateTarFile", default=False, action="store_true", help="Skip creating the CMSSW tarball.")
    parser.add_argument("--use_custom_eos_cmd",
                        default='eos root://cmseos.fnal.gov find -name "*.root" /store/group/lnujj/VVjj_aQGC/custom_nanoAOD ',
                        help="Custom EOS command to list files for a dataset (it will be concatenated with the dataset name).")
    parser.add_argument("--input_file", required=True, help="Path (under input_data_Files/) of the input list file.")
    parser.add_argument("--eos_output_path", default="", help="EOS base path for output files. Default: /eos/home-p/pelai/HZa/mc_NATool")
    parser.add_argument("--condor_log_path", default="./", help="Directory for condor logs.")
    parser.add_argument("--condor_queue", default="testmatch", help=(
        "Condor queue options:\n"
        "  name            Duration\n"
        "  ------------------------\n"
        "  espresso            20min\n"
        "  microcentury         1h\n"
        "  longlunch            2h\n"
        "  workday              8h\n"
        "  tomorrow             1d\n"
        "  testmatch            3d\n"
        "  nextweek             1w\n"
    ))
    parser.add_argument("--post_proc", default="post_proc.py", help="Post process script to run in the job.")
    parser.add_argument("--year", default="2017", type=str, help="Year of data taking.")
    parser.add_argument("--isMC", default=False, action="store_true", help="Indicate if the input is MC.")
    parser.add_argument("--transfer_input_files", default="keep_and_drop.txt", help="Extra files to be transferred with the job.")
    parser.add_argument("--eos_xrootd_host", default="root://eosuser.cern.ch/",
                        help="Default XRootD host for translating /eos/... local paths to remote URLs.")

    args = parser.parse_args()
    main(args)
