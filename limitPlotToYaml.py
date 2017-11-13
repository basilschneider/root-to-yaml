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

def init_axis(title="title", unit=""):
    return {"header": {"name": title, "units": unit}, "values": []}

def th2_to_data(h2, xmin=-1, xmax=-1, ymin=-1, ymax=-1, zMultiplier=1., binCenter=False):
    data = [[],[],[]]
    for xbin in range(1, h2.GetNbinsX()+2):
        xbinMin = h2.GetXaxis().GetBinLowEdge(xbin)
        xbinMax = h2.GetXaxis().GetBinUpEdge(xbin)
        if xmin>0 and xbinMin < xmin or xmax>0 and xbinMax > xmax: continue
        for ybin in range(1, h2.GetNbinsY()+2):
            ybinMin = h2.GetYaxis().GetBinLowEdge(ybin)
            ybinMax = h2.GetYaxis().GetBinUpEdge(ybin)
            if ymin>0 and ybinMin < ymin or ymax>0 and ybinMax > ymax: continue
            content = h2.GetBinContent(xbin, ybin)
            if content < 1e-8: continue
            if binCenter:
                data[0].append({"value": h2.GetXaxis().GetBinCenter(xbin)})
                data[1].append({"value": h2.GetYaxis().GetBinCenter(ybin)})
            else:
                data[0].append({"low": xbinMin, "high": xbinMax})
                data[1].append({"low": ybinMin, "high": ybinMax})
            data[2].append({"value": content*zMultiplier})
    return data

def th2_to_yaml(data, xAxis, yAxis, qualifiers=[], zUnit="PB"):
    h2yaml = {
        "independent_variables": [xAxis, yAxis],
        "dependent_variables": [{"header": {"name": "SIG", "units": zUnit}, "qualifiers": qualifiers, "values": []}]
    }
    h2yaml["independent_variables"][0]["values"] = data[0]
    h2yaml["independent_variables"][1]["values"] = data[1]
    h2yaml["dependent_variables"][0]["values"] = data[2]
    return h2yaml

def tgraph2d_to_data(gr, xmin=-1, xmax=-1, ymin=-1, ymax=-1, zMultiplier=1.):
    data = [[], [], []]
    for n in range(gr.GetN()):
        x, y = gr.GetX()[n], gr.GetY()[n]
        if xmin>0 and x < xmin or xmax>0 and xmax>0 and x > xmax: continue
        if ymin>0 and y < ymin or ymax>0 and ymax>0 and y > ymax: continue
        data[0].append({"value": x})
        data[1].append({"value": y})
        data[2].append({"value": gr.GetZ()[n]*zMultiplier})
    # Sort by x*1e6+y, so for reasonable small y, the data is sorted by x and then by y
    data = [list(x) for x in zip(*sorted(zip(data[0], data[1], data[2]), key=lambda triple: triple[0]["value"]*1e6+triple[1]["value"]))]
    return data

def tgraph2d_to_yaml(data, xAxis, yAxis, qualifiers=[], zUnit="PB"):
    gr_yaml = {
        "independent_variables": [xAxis, yAxis],
        "dependent_variables": [{"header": {"name": "SIG", "units": zUnit}, "qualifiers": qualifiers, "values": []}]
    }
    gr_yaml["independent_variables"][0]["values"] = data[0]
    gr_yaml["independent_variables"][1]["values"] = data[1]
    gr_yaml["dependent_variables"][0]["values"] = data[2]
    return gr_yaml

def tgraph_to_data(gr):
    data = [[], []]
    for n in range(gr.GetN()):
        data[0].append({"value": round(gr.GetX()[n], 2)})
        data[1].append({"value": round(gr.GetY()[n], 2)})
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

def convertToYaml(cfg, section):
    xmin = cfg.getfloat(section, "xmin")
    xmax = cfg.getfloat(section, "xmax")
    ymin = cfg.getfloat(section, "ymin")
    ymax = cfg.getfloat(section, "ymax")
    infile = cfg.get(section, "input_file")
    zUnit = cfg.get(section, "zUnit")
    zMultiplier = cfg.getfloat(section, "zMultiplier")
    binCenter = cfg.getboolean(section, "binCenter")

    xAxis = init_axis(cfg.get(section, "xTitle"), cfg.get(section, "xUnit"))
    yAxis = init_axis(cfg.get(section, "yTitle"), cfg.get(section, "yUnit"))

    qualifiers = [
        {"name": "RE", "value": cfg.get(section, "process")},
        {"name": "SQRT(S)", "value": cfg.getfloat(section, "com_energy"), "units": "GEV"},
        {"name": "INTEGRATED LUMINOSITY", "value": cfg.getfloat(section, "int_lumi"), "units": "1/FB"},
    ]

    for name in cfg.get(section, "objects").split(","):
        name = name.strip()
        obj = getFromFile(infile, name)
        if not obj: continue
        if isinstance(obj, ROOT.TH2):
            yaml_obj = th2_to_yaml(th2_to_data(obj, xmin, xmax, ymin, ymax, zMultiplier, binCenter), xAxis, yAxis, qualifiers, zUnit)
        elif isinstance(obj, ROOT.TGraph2D):
            yaml_obj = tgraph2d_to_yaml(tgraph2d_to_data(obj, xmin, xmax, ymin, ymax, zMultiplier), xAxis, yAxis, qualifiers, zUnit)
        elif isinstance(obj, ROOT.TGraph):
            yaml_obj = tgraph_to_yaml(tgraph_to_data(obj), xAxis, yAxis, qualifiers)
        else:
            print "Do not know what to do with class", type(obj)

        yamlName = "{}_{}.yaml".format(section,name)
        with open(yamlName, "w") as f:
            print "Write to", yamlName
            yaml.dump(yaml_obj, f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Converts limit plots to YAML (for HEPData).')
    parser.add_argument('cfgFile', nargs='+', default=["config.cfg"],
                        help="Configuration files")
    args = parser.parse_args()

    cfg = ConfigParser.SafeConfigParser()
    cfg.read(args.cfgFile)

    for section in cfg.sections():
        convertToYaml(cfg, section)
