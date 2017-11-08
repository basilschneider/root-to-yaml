#!/usr/bin/env python2
import argparse
import ConfigParser
import os
import sys
import ROOT
import yaml
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

def getFromFile(filename, objectname):
    f = ROOT.TFile(filename)
    h = f.Get(objectname)
    if not h:
        print "Object '{}' not found in file '{}'".format(objectname, filename)
        return
        raise IOError("Object '{}' not found in file '{}'".format(objectname, filename))
    h = ROOT.gROOT.CloneObject(h)
    return h

def getH2():
    limitFile = "$HOME/phd/plotter/limitCalculations/T5Wg_v11/saved_graphs1d_limit.root"
    h2_name_observed = "obs_hist"
    h2 = getFromFile(limitFile, h2_name_observed)
    return h2

def th2_to_data(h2, xmin=-1, xmax=-1, ymin=-1, ymax=-1):
    data = [[],[],[]]
    for xbin in range(1, h2.GetNbinsX()+2):
        xbinMin = h2.GetXaxis().GetBinLowEdge(xbin)
        xbinMax = h2.GetXaxis().GetBinUpEdge(xbin)
        if xmin>0 and xbinMin < xmin or xmax>0 and xmax>0 and xbinMax > xmax: continue
        for ybin in range(1, h2.GetNbinsY()+2):
            ybinMin = h2.GetYaxis().GetBinLowEdge(ybin)
            ybinMax = h2.GetYaxis().GetBinUpEdge(ybin)
            if ymin>0 and ybinMin < ymin or ymax>0 and ybinMax > ymax: continue
            content = h2.GetBinContent(xbin, ybin)
            if content < 1e-8: continue
            data[0].append({"low": xbinMin, "high": xbinMax})
            data[1].append({"low": ybinMin, "high": ybinMax})
            data[2].append({"value": content})
    return data

def tgraph_to_yaml(data, xAxis, yAxis, qualifiers=[]):
    gr_yaml = {
        "independent_variables": [xAxis],
        "dependent_variables": [yAxis]
    }
    gr_yaml["dependent_variables"][0]["qualifiers"] = qualifiers
    gr_yaml["independent_variables"][0]["values"] = data[0]
    gr_yaml["dependent_variables"][0]["values"] = data[1]
    return gr_yaml

def init_axis(title="title", unit=""):
    return {"header": {"name": title, "units": unit}, "values": []}

def tgraph_to_data(gr):
    data = [[],[]]
    for n in range(gr.GetN()):
        data[0].append({"value": gr.GetX()[n]})
        data[1].append({"value": gr.GetY()[n]})
    return data

def th2_to_yaml(data, xAxis, yAxis, qualifiers=[]):
    h2yaml = {
        "independent_variables": [xAxis, yAxis],
        "dependent_variables": [{"header": {"name": "SIG", "units": "FB"}, "qualifiers": qualifiers, "values": []}]
    }
    h2yaml["independent_variables"][0]["values"] = data[0]
    h2yaml["independent_variables"][1]["values"] = data[1]
    h2yaml["dependent_variables"][0]["values"] = data[2]
    return h2yaml

def convertToYaml(cfg, section, output):
    xmin = cfg.getfloat(section, "xmin")
    xmax = cfg.getfloat(section, "xmax")
    ymin = cfg.getfloat(section, "ymin")
    ymax = cfg.getfloat(section, "ymax")
    infile = cfg.get(section, "input_file")

    xAxis = init_axis(cfg.get(section, "xTitle"), cfg.get(section, "xUnit"))
    yAxis = init_axis(cfg.get(section, "yTitle"), cfg.get(section, "yUnit"))

    qualifiers = [
        {"name": "RE", "value": cfg.get(section, "process")},
        {"name": "SQRT(S)", "value": cfg.getfloat(section, "com_energy"), "units": "GEV"},
        {"name": "INTEGRATED LUMINOSITY", "value": cfg.getfloat(section, "int_lumi"), "units": "1/FB"},
    ]

    h2 = getFromFile(infile, cfg.get(section, "obs_hist"))
    if h2:
        with open(section+"_h2.yaml", "w") as f:
            h2yaml = th2_to_yaml(th2_to_data(h2, xmin, xmax, ymin, ymax), xAxis, yAxis, qualifiers)
            yaml.dump(h2yaml, f)

    gr_obs = getFromFile(infile, cfg.get(section, "gr_obs"))
    if gr_obs:
        with open(section+"_obs.yaml", "w") as f:
            obs_yaml = tgraph_to_yaml(tgraph_to_data(gr_obs), xAxis, yAxis, qualifiers)
            yaml.dump(obs_yaml, f)

    gr_exp = getFromFile(infile, cfg.get(section, "gr_exp"))
    if gr_exp:
        with open(section+"_exp.yaml", "w") as f:
            exp_yaml = tgraph_to_yaml(tgraph_to_data(gr_exp), xAxis, yAxis, qualifiers)
            yaml.dump(exp_yaml, f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Converts limit plots to YAML (for HEPData).')
    parser.add_argument('cfgFile', nargs='+', default=["config.cfg"],
                        help="Configuration files")
    parser.add_argument('--out', default="out.xyz", help="Output file name")
    args = parser.parse_args()

    cfg = ConfigParser.SafeConfigParser()
    cfg.read(args.cfgFile)

    for section in cfg.sections():
        convertToYaml(cfg, section, args.out)
