#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import argparse
import subprocess

# -------------------------------
# Helpers
# -------------------------------

def str2bool(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("yes", "true", "t", "y", "1"):
        return True
    if s in ("no", "false", "f", "n", "0"):
        return False
    raise argparse.ArgumentTypeError("Boolean value expected; got '{}'".format(v))

# ---- ROOT & correctionlib preloading (no pathlib) ----
def preload_correctionlib():
    """Preload libcorrectionlib for ROOT/cling so C++ symbols resolve."""
    try:
        import ROOT  # noqa
    except Exception as e:
        print("[WARN] ROOT import failed early: {}".format(e))

    try:
        import correctionlib
        import ROOT
        libdir = os.path.join(os.path.dirname(correctionlib.__file__), "lib")
        if os.path.exists(libdir):
            ROOT.gSystem.AddDynamicPath(libdir)
            for soname in ("libcorrectionlib", "libcorrectionlib.so"):
                rc = ROOT.gSystem.Load(soname)
                print("[INFO] Try load {}: rc={}".format(soname, rc))
                if rc == 0:
                    print("[OK] Loaded {} from {}".format(soname, libdir))
                    break
            os.environ["LD_LIBRARY_PATH"] = "{}:{}".format(libdir, os.environ.get("LD_LIBRARY_PATH",""))
        else:
            print("[WARN] correctionlib found but no lib/ directory next to package")
    except Exception as e:
        print("[WARN] Could not preload correctionlib C++ lib: {}. Will proceed".format(e))

# ---- subprocess helper (py2-friendly) ----
def _popen_capture(cmdlist):
    try:
        p = subprocess.Popen(cmdlist, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        rc = p.returncode
        # py2 bytes decode
        try:
            out = out.decode("utf-8")
        except Exception:
            try:
                out = out.decode("latin-1")
            except Exception:
                out = str(out)
        try:
            err = err.decode("utf-8")
        except Exception:
            try:
                err = err.decode("latin-1")
            except Exception:
                err = str(err)
        return rc, out, err
    except OSError as e:
        return 127, "", str(e)

# ---- X509 proxy helpers ----
def have_valid_proxy():
    rc, out, err = _popen_capture(["voms-proxy-info", "-e"])
    if rc == 127:
        print("[WARN] voms-proxy-info not found; skip proxy check.")
        return True
    return (rc == 0)

def ensure_proxy_env():
    rc, out, err = _popen_capture(["voms-proxy-info", "--path"])
    if rc == 0:
        path = out.strip()
        if path:
            os.environ["X509_USER_PROXY"] = path
            print("[INFO] X509_USER_PROXY set to {}".format(path))

# -------------------------------
# XRootD URL utilities with strict //store handling
# -------------------------------

def _join_redirector(redirector, abs_store_suffix):
    """
    Ensure final URL is 'root://host//store/...'.
    redirector: e.g. 'root://cms-xrd-global.cern.ch' (with or without trailing '/')
    abs_store_suffix: must start with '/store/...'
    """
    r = redirector.rstrip('/')                 # -> 'root://host'
    s = '//' + abs_store_suffix.lstrip('/')    # -> '//store/...'
    return r + s                               # -> 'root://host//store/...'


def _to_urls_for_both_redirectors(path):
    """
    Return (url_cern, url_infn) for a CMS /store path or an existing root:// URL.
    If not a CMS path, return (path, path).
    """
    CERN_REDIRECTOR = "root://cms-xrd-global.cern.ch/"
    INFN_REDIRECTOR = "root://xrootd-cms.infn.it/"

    # Build abs_store = '/store/...'
    if path.startswith("/store/"):
        abs_store = path
    elif path.startswith("root://"):
        suffix = path.split("//", 1)[-1].lstrip("/")
        if "store/" in suffix:
            tail = suffix.split("store/", 1)[-1]
            abs_store = "/store/" + tail
        else:
            return (path, path)  # not a CMS storage path
    else:
        return (path, path)      # local or other protocol

    url_infn = _join_redirector(INFN_REDIRECTOR, abs_store)
    url_cern = _join_redirector(CERN_REDIRECTOR, abs_store)
    return (url_cern, url_infn)

def open_with_fallback(path):
    """
    Use ROOT.TFile.Open with CERN->INFN fallback.
    Returns opened TFile, or raises RuntimeError.
    """
    import ROOT

    # Local file short-circuit
    if (not path.startswith("root://")) and os.path.exists(path):
        f = ROOT.TFile.Open(path)
        if f and (not f.IsZombie()):
            print("[OK] Opened local file: {}".format(path))
            return f
        raise RuntimeError("Cannot open local file: {}".format(path))

    url_cern, url_infn = _to_urls_for_both_redirectors(path)

    f = ROOT.TFile.Open(url_cern)
    if f and (not f.IsZombie()):
        print("[OK] Opened via CERN redirector: {}".format(url_cern))
        return f

    print("[WARN] CERN redirector failed, trying INFN...")
    f = ROOT.TFile.Open(url_infn)
    if f and (not f.IsZombie()):
        print("[OK] Opened via INFN redirector: {}".format(url_infn))
        return f

    raise RuntimeError("Both CERN and INFN redirectors failed for path: {}".format(path))

def resolve_with_fallback(path):
    """
    Return a final usable URL/path string:
    - /store path: test CERN then INFN, return whichever works
    - root:// path: same
    - local path: return if exists
    """
    if (not path.startswith("root://")) and os.path.exists(path):
        return path

    url_cern, url_infn = _to_urls_for_both_redirectors(path)

    # Light-weight probe: try CERN; if ok return CERN, else INFN
    try:
        import ROOT
        tf = ROOT.TFile.Open(url_cern)
        if tf and (not tf.IsZombie()):
            tf.Close()
            return url_cern
    except Exception:
        pass

    try:
        import ROOT
        tf = ROOT.TFile.Open(url_infn)
        if tf and (not tf.IsZombie()):
            tf.Close()
            return url_infn
    except Exception:
        pass

    # Both failed; return original so upstream error shows original path
    return path

def to_global_xrootd(path):
    """
    Normalize display to chosen redirector (env CMS_XRD_REDIRECTOR),
    ensuring 'root://host//store/...'.
    """
    redirector = os.environ.get("CMS_XRD_REDIRECTOR", "root://xrootd-cms.infn.it/")
    if path.startswith("/store/"):
        return _join_redirector(redirector, path)
    if path.startswith("root://cms-xrd-global.cern.ch/") or path.startswith("root://xrootd-cms.infn.it/"):
        suffix = path.split("//", 1)[-1].lstrip("/")
        if "store/" in suffix:
            tail = suffix.split("store/", 1)[-1]
            return _join_redirector(redirector, "/store/" + tail)
        return path
    return path

# ---- Safe open preflight (uses fallback) ----
def preflight_open_first_file(flist):
    if not flist:
        return
    try:
        import ROOT
        f0 = str(flist[0])
        tf = open_with_fallback(f0)
        t = tf.Get("Events")
        if not t:
            raise RuntimeError("'Events' tree not found in: {}".format(f0))
        tf.Close()
        print("[OK] Preflight open succeeded: {}".format(f0))
    except Exception as e:
        print("[ERROR] Preflight open failed: {}".format(e))
        raise

# -------------------------------
# NanoAODTools imports
# -------------------------------
from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor import PostProcessor
from PhysicsTools.NanoAODTools.postprocessing.modules.jme.jetmetHelperRun2 import createJMECorrector
from PhysicsTools.NanoAODTools.postprocessing.modules.btv.btagSFProducer import btagSFProducer
from PhysicsTools.NanoAODTools.postprocessing.modules.common.puWeightProducer import *
from PhysicsTools.NanoAODTools.postprocessing.modules.common.PrefireCorr import *
from PhysicsTools.NanoAODTools.postprocessing.modules.common.muonScaleResProducer import *
from PhysicsTools.NanoAODTools.postprocessing.modules.common.LHEScaleWeightProducer import LHEScaleWeightProducer
from ggTemporaryScale import gammaSFProducer

# Custom modules
from HZg_AnalysisModule import *
from JetSFMaker import *

# -------------------------------
# CLI
# -------------------------------
def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputFile", default="", type=str, help="Input .root or .txt list")
    parser.add_argument("-n", "--entriesToRun", default=100, type=int, help="0 means all entries")
    parser.add_argument("-d", "--DownloadFileToLocalThenRun", default=True, type=str2bool, help="Prefetch to local then run")
    parser.add_argument("-y", "--moduleyear", default="2017", type=str, help="2016preVFP/2016postVFP/2017/2018/2022preEE/2022postEE/2023preBPix/2023postBPix")
    parser.add_argument("-m", "--isMC", default=True, type=str2bool, help="True for MC, False for data")
    return parser.parse_args()

def getListFromFile(filename):
    with open(filename, "r") as f:
        raw = [line.strip() for line in f if line.strip()]
    resolved = []
    for p in raw:
        url = resolve_with_fallback(p)
        resolved.append(url)
    print("[INFO] Resolved {} entries with CERN→INFN fallback.".format(len(resolved)))
    return resolved

# -------------------------------
# Main
# -------------------------------
def main():
    preload_correctionlib()
    args = parse_arguments()

    testfilelist = []
    modulesToRun = []
    isMC = args.isMC
    moduleyear = args.moduleyear
    print("what isMC: {}".format(isMC))
    entriesToRun = int(args.entriesToRun)
    DownloadFileToLocalThenRun = args.DownloadFileToLocalThenRun

    # Input list + fallback resolve
    if args.inputFile.endswith(".txt"):
        testfilelist = getListFromFile(args.inputFile)
    elif args.inputFile.endswith(".root"):
        testfilelist.append(resolve_with_fallback(args.inputFile))
    else:
        print("INFO: No input file specified. Using default file list.")
        testfilelist = getListFromFile("ExampleInputFileList.txt")

    print("DEBUG: Input file list: {}".format(testfilelist))
    if len(testfilelist) == 0:
        print("ERROR: No input files found. Exiting.")
        sys.exit(1)

    # Proxy checks only if reading from xrootd
    needs_proxy = any(p.startswith("root://") and "/store/" in p for p in testfilelist)
    if needs_proxy:
        ensure_proxy_env()
        if not have_valid_proxy():
            print("[ERROR] No valid VOMS proxy. Run: voms-proxy-init -voms cms -rfc --valid 192:00")
            sys.exit(2)

    # Preflight open (uses fallback)
    try:
        preflight_open_first_file(testfilelist)
    except Exception:
        sys.exit(3)

    # -------------------------------
    # Year-specific config
    # -------------------------------
    year = None
    cfgFile = None
    jsonFileName = None
    sfFileName = None

    if moduleyear == "2023postBPix":
        year = moduleyear
        cfgFile = "Input_2023postBPix.yml"
        jsonFileName = "golden_Json/Cert_Collisions2023_366442_370790_Golden.json"
        LHEScaleSF  = lambda : LHEScaleWeightProducer("2023BPix")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="2023postBPix", jesUncert="All", jetType="AK4PFPuppi", applyHEMfix=True)
        modulesToRun.extend([jetmetCorrector(), muonScaleResRun3_2023BPix()])

    if moduleyear == "2023preBPix":
        year = moduleyear
        cfgFile = "Input_2023preBPix.yml"
        jsonFileName = "golden_Json/Cert_Collisions2023_366442_370790_Golden.json"
        LHEScaleSF  = lambda : LHEScaleWeightProducer("2023")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="2023preBPix", jesUncert="All", jetType="AK4PFPuppi", applyHEMfix=True)
        modulesToRun.extend([jetmetCorrector(), muonScaleResRun3_2023()])

    if moduleyear == "2022postEE":
        year = moduleyear
        cfgFile = "Input_2022postEE.yml"
        jsonFileName = "golden_Json/Cert_Collisions2022_355100_362760_Golden.json"
        LHEScaleSF  = lambda : LHEScaleWeightProducer("2022EE")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="2022postEE", jesUncert="All", jetType="AK4PFPuppi", applyHEMfix=True)
        modulesToRun.extend([jetmetCorrector(), muonScaleResRun3_2022EE()])

    if moduleyear == "2022preEE":
        year = moduleyear
        cfgFile = "Input_2022preEE.yml"
        jsonFileName = "golden_Json/Cert_Collisions2022_355100_362760_Golden.json"
        LHEScaleSF  = lambda : LHEScaleWeightProducer("2022")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="2022preEE", jesUncert="All", jetType="AK4PFPuppi", applyHEMfix=True)
        modulesToRun.extend([jetmetCorrector(), muonScaleResRun3_2022()])

    if moduleyear == "2018":
        year = moduleyear
        cfgFile = "Input_2018.yml"
        jsonFileName = "golden_Json/Cert_314472-325175_13TeV_Legacy2018_Collisions18_JSON.txt"
        sfFileName = "DeepCSV_102XSF_V2.csv"
        HZg_AnalysisModule = lambda: HZg_AnalysisProducer(2018)
        LHEScaleSF  = lambda : LHEScaleWeightProducer("UL18")
        gammaSF = lambda: gammaSFProducer("UL18")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="UL2018", jesUncert="All", jetType="AK4PFchs", applyHEMfix=True)
        puidSF = lambda: JetSFMaker("{}".format(2018))
        modulesToRun.extend([jetmetCorrector(), puidSF(), gammaSF(), puAutoWeight_UL2018(), muonScaleRes2018()])

    if moduleyear == "2017":
        year = moduleyear
        cfgFile = "Input_2017.yml"
        jsonFileName = "golden_Json/Cert_294927-306462_13TeV_UL2017_Collisions17_GoldenJSON.txt"
        sfFileName = "DeepCSV_102XSF_V2.csv"
        HZg_AnalysisModule = lambda: HZg_AnalysisProducer(2017)
        LHEScaleSF  = lambda : LHEScaleWeightProducer("UL17")
        gammaSF = lambda: gammaSFProducer("UL17")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="UL2017", jesUncert="All", jetType="AK4PFchs", applyHEMfix=False)
        PrefireCorr2017 = lambda : PrefCorr('L1prefiring_jetpt_2017BtoF.root', 'L1prefiring_jetpt_2017BtoF',
                                            'L1prefiring_photonpt_2017BtoF.root', 'L1prefiring_photonpt_2017BtoF')
        puidSF = lambda: JetSFMaker("{}".format(2017))
        modulesToRun.extend([jetmetCorrector(), puidSF(), gammaSF(), PrefireCorr2017(), puAutoWeight_UL2017(), muonScaleRes2017()])

    if moduleyear == "2016preVFP":
        year = moduleyear
        jsonFileName = "golden_Json/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
        sfFileName = "DeepCSV_102XSF_V2.csv"
        HZg_AnalysisModule = lambda: HZg_AnalysisProducer(2016)
        LHEScaleSF  = lambda : LHEScaleWeightProducer("2016")
        gammaSF = lambda: gammaSFProducer("UL16Pre-VFP")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="UL2016_preVFP", jesUncert="All", jetType="AK4PFchs", applyHEMfix=False)
        PrefireCorr2016 = lambda : PrefCorr("L1prefiring_jetpt_2016BtoH.root", "L1prefiring_jetpt_2016BtoH",
                                            "L1prefiring_photonpt_2016BtoH.root", "L1prefiring_photonpt_2016BtoH")
        puidSF = lambda: JetSFMaker("{}".format(2016))
        modulesToRun.extend([jetmetCorrector(), puidSF(), gammaSF(), PrefireCorr2016(), puAutoweight_UL2016PreVFP(), muonScaleRes2016_UL16PreVFP()])

    if moduleyear == "2016postVFP":
        year = moduleyear
        jsonFileName = "golden_Json/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
        sfFileName = "DeepCSV_102XSF_V2.csv"
        HZg_AnalysisModule = lambda: HZg_AnalysisProducer(2016)
        LHEScaleSF  = lambda : LHEScaleWeightProducer("2016post")
        gammaSF = lambda: gammaSFProducer("UL16Post-VFP")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="UL2016", jesUncert="All", jetType="AK4PFchs", applyHEMfix=False)
        PrefireCorr2016 = lambda : PrefCorr("L1prefiring_jetpt_2016BtoH.root", "L1prefiring_jetpt_2016BtoH",
                                            "L1prefiring_photonpt_2016BtoH.root", "L1prefiring_photonpt_2016BtoH")
        puidSF = lambda: JetSFMaker("{}".format(2016))
        modulesToRun.extend([jetmetCorrector(), puidSF(), gammaSF(), PrefireCorr2016(), puAutoweight_UL2016PostVFP(), muonScaleRes2016_UL16PostVFP()])

    # -------------------------------
    # Run PostProcessor
    # -------------------------------
    if isMC:
        if int(moduleyear[:4]) < 2020:
            p = PostProcessor(
                ".",
                testfilelist, None, None,
                modules=modulesToRun, provenance=True, fwkJobReport=False,
                haddFileName="skimmed_nano_mc.root",
                maxEntries=entriesToRun,
                prefetch=DownloadFileToLocalThenRun,
                outputbranchsel="keep_and_drop.txt"
            )
        elif int(moduleyear[:4]) > 2020:
            p = PostProcessor(
                ".",
                testfilelist, None, None,
                modules=modulesToRun, provenance=True, fwkJobReport=False,
                haddFileName="skimmed_nano_mc.root",
                maxEntries=entriesToRun,
                prefetch=DownloadFileToLocalThenRun,
                outputbranchsel="keep_and_drop_run3.txt"
            )
    else:
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear=year, jesUncert="All", jetType="AK4PFchs")
        modulesToRun.extend([jetmetCorrector()])
        p = PostProcessor(
            ".",
            testfilelist, None, None,
            modules=modulesToRun, provenance=True, fwkJobReport=False,
            haddFileName="skimmed_nano_data.root",
            jsonInput=jsonFileName,
            maxEntries=entriesToRun,
            prefetch=DownloadFileToLocalThenRun,
            outputbranchsel="keep_and_drop_data.txt"
        )

    p.run()

if __name__ == "__main__":
    main()
