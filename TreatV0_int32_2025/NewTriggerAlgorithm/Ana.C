#include <iostream>
#include "TFile.h"
#include "TTree.h"
#include "TH1D.h"
#include "TString.h"
using namespace std;

void PreAna(TString input_file = "");

int Ana() {
    PreAna("../light.root");
    return 0;
}
void PreAna(TString input_file)
{
    Double_t fs = 5000.;
    //ADC to voltage converter;
    Double_t vol = 1.0*2*10/(TMath::Power(2,24)-1);
    /*    
          []      "trigpos",
          [0]     "rawamp",
          [1]     "filamp",
          [2]     "baseline",
          [3]     "baselineRMS",
          [4]     "correlation",
          [5]     "tv",
          [6]     "tvl",
          [7]     "tvr",
          [8]     "SI",
          [9]     "baseline_slope",
          [10]    "fitted_baseline",
          [11]    "fitted_rawamp",
          [12]    "risetime",
          [13]    "decaytime",
          [14]    "delayamp",
          [15]    "meantime",
          [16]    "rawarea",
          [17]    "filarea",
          [18]    "correlation_narrow"
          */
    // Clear previously defined objects if any
    gDirectory->Delete("all");
    std::string branches[] = {"trigpos","rawamp","filamp","baseline","baselineRMS","correlation","tv","tvl","tvr","SI","baseline_slope","fitted_baseline","fitted_rawamp","risetime","decaytime","delayamp","meantime","rawarea","filarea","correlation_narrow"};
    Long64_t first_entry = 0;
    Double_t entries[19] = {0.0};
    const int float_entries = 19;

    TFile *infile = new TFile(input_file);
    TTree *t1 = (TTree*)infile->Get("tree1");
    t1->SetBranchAddress(branches[0].c_str(), &first_entry);
    for(int i=0; i < float_entries; i++){
        t1->SetBranchAddress(branches[i+1].c_str(), &entries[i]);
    }

    TString filename = input_file;
    filename.Remove(0,filename.Last('/')+1);
    filename.Remove(filename.Last('.'));

    //TH1::SetDefaultSumw2();
    const Int_t Nbin = 3000;
    TH1D *hamp1 = new TH1D("hamp1"," ;Amplitude;Counts", Nbin,0,300000);
    TH1D *hamp2 = new TH1D("hamp2"," ;Amplitude;Counts", Nbin,0,300000);
    TH1D *hamp3 = new TH1D("hamp3"," ;Amplitude;Counts", Nbin,0,300000);
    hamp1->SetLineColor(kRed);



    TGraph *gr[20];
    for(int i=0; i < 20; i++){
        gr[i] = new TGraph();
        gr[i]->GetXaxis()->SetTitle("Filtered amp (#muV)");
        gr[i]->SetMarkerStyle(7);
        gr[i]->SetMarkerColor(kBlue);
    }
    gr[0]->SetMarkerColor(kRed);

    Int_t kgr[10] = {0};
    Int_t Num = t1->GetEntries();
    t1->GetEntry(1);
    cout<<first_entry<<"\t"<<entries[17]<<endl;
    Int_t tmp_pos = 0;
    Float_t Time = 0.0;
    Float_t new_amp = 0.0;
    Float_t ave_amp = 0.0;

    // Deactivate all branches
    t1->SetBranchStatus("*", 0);
    // Activate only four of them
    for (auto activeBranchName : {"trigpos", "filamp"})
        t1->SetBranchStatus(activeBranchName, 1);

    Float_t ene = 0.0;
    for(int i=0; i < Num; i++){
        t1->GetEntry(i);
        /*
        if(first_entry<tmp_pos){
            Time += tmp_pos*1.0/5000/3600;
            cout<<Time<<endl;
        }
        tmp_pos = first_entry;
        */
        kgr[1] += 1;
        //Baseline RMS cut
        //if(entries[3] > 260)continue;
        //if(entries[4] < 0.9)continue;
        /*
        //For selecting tl-208 line
        //correlation cut
        if(entries[4] < 0.999)continue;
        //Amp cut
        if(entries[1] > 2.05E5)continue;
        if(entries[1] < 1.96E5)continue;
        */
        /*
           if(entries[12]/entries[1] < 0.03){
           kgr[5] += 1;
           gr[0]->SetPoint(kgr[5], (first_entry/2000./3600+Time)/4, entries[2]);}
           */
        /*
           new_amp = entries[1]*100*(1.0/(entries[2]*-0.02058+190013));
           if(new_amp < 99.6)continue;
           if(new_amp > 100.6)continue;
           */
        kgr[0] += 1;
        ave_amp += entries[1];
        /*
        */
        if(entries[2]<-380000){
            new_amp = entries[1]*261400*(1.0/(entries[2]*-0.0209239+191274));
        }
        else{
            new_amp = entries[1]*261400*(1.0/(entries[2]*-0.0184512+192654));
        }
        //if(new_amp > 10E5)continue;
        ene = new_amp*1.00e-02+new_amp*new_amp*-2.17879e-10;
        //new_amp = entries[1]*261400/(96706.5-0.036539*entries[0]-1.58e-9*entries[0]*entries[0]);
        new_amp = entries[1];


        gr[1]->SetPoint(kgr[0], (first_entry/fs/3600), 1000*vol*entries[2]);
        gr[2]->SetPoint(kgr[0], (first_entry/fs/3600), 1000*vol*entries[3]);
        gr[3]->SetPoint(kgr[0], new_amp, entries[4]);
        gr[4]->SetPoint(kgr[0], new_amp, entries[5]);
        gr[5]->SetPoint(kgr[0], new_amp, entries[6]);
        gr[6]->SetPoint(kgr[0], new_amp, entries[7]);
        gr[7]->SetPoint(kgr[0], new_amp, entries[12]);
        gr[8]->SetPoint(kgr[0], new_amp, entries[13]);
        gr[9]->SetPoint(kgr[0],  new_amp, entries[14]);
        gr[10]->SetPoint(kgr[0], new_amp, entries[15]);
        gr[11]->SetPoint(kgr[0], new_amp, entries[16]);
        gr[12]->SetPoint(kgr[0], new_amp, entries[17]);
        gr[13]->SetPoint(kgr[0], new_amp, entries[18]);
        gr[14]->SetPoint(kgr[0], 1000*entries[6], 1000*entries[7]);
        gr[15]->SetPoint(kgr[0], entries[12], entries[13]);
        gr[16]->SetPoint(kgr[0], entries[2], entries[10]);
        gr[17]->SetPoint(kgr[0], entries[2], new_amp);
        gr[18]->SetPoint(kgr[0], new_amp, entries[11]/new_amp);
        gr[19]->SetPoint(kgr[0], new_amp, entries[14]/new_amp);
        hamp1->Fill(new_amp);
        hamp2->Fill(entries[1]);
        hamp3->Fill(entries[8]);
        //if(ene < 5000-20)continue;
        //if(ene > 1460+20)continue;
    }
    TCanvas *cg1 = new TCanvas("cg1", "cg1", 0, 0, 800, 600);
    gr[1]->Draw("AP");
    gr[1]->GetXaxis()->SetTitle("Time (hour)");
    gr[1]->GetYaxis()->SetTitle("Baseline (mV)");
    TCanvas *cg2 = new TCanvas("cg2", "cg2", 0, 0, 800, 600);
    gr[2]->Draw("AP");
    gr[2]->GetXaxis()->SetTitle("Time (hour)");
    gr[2]->GetYaxis()->SetTitle("Baseline RMS (mV)");
    TCanvas *cg3 = new TCanvas("cg3", "cg3", 0, 0, 800, 600);
    gr[3]->Draw("AP");
    gr[3]->GetYaxis()->SetTitle("Correlation");
    /*
    */
    TCanvas *cg9 = new TCanvas("cg9", "cg9", 0, 0, 800, 600);
    gr[9]->Draw("AP");
    gr[9]->GetYaxis()->SetTitle("Delayed amp (#muV)/Amp");
    TCanvas *cg10 = new TCanvas("cg10", "cg10", 0, 0, 800, 600);
    gr[10]->Draw("AP");
    gr[10]->GetYaxis()->SetTitle("Mean time (s)/Amp");
    TCanvas *cg11 = new TCanvas("cg11", "cg11", 0, 0, 800, 600);
    gr[11]->Draw("AP");
    gr[11]->GetYaxis()->SetTitle("Area raw/Amp");
    TCanvas *cg12 = new TCanvas("cg12", "cg12", 0, 0, 800, 600);
    gr[12]->Draw("AP");
    gr[12]->GetYaxis()->SetTitle("Area filt/Amp");
    TCanvas *cg4 = new TCanvas("cg4", "cg4", 0, 0, 800, 600);
    gr[4]->Draw("AP");
    gr[4]->GetYaxis()->SetTitle("TV");
    TCanvas *cg5 = new TCanvas("cg5", "cg5", 0, 0, 800, 600);
    gr[5]->Draw("AP");
    gr[5]->GetYaxis()->SetTitle("TVL");
    TCanvas *cg6 = new TCanvas("cg6", "cg6", 0, 0, 800, 600);
    gr[6]->Draw("AP");
    gr[6]->GetYaxis()->SetTitle("TVR");
    TCanvas *cg14 = new TCanvas("cg14", "cg14", 0, 0, 800, 600);
    gr[14]->Draw("AP");
    gr[14]->GetXaxis()->SetTitle("TVL");
    gr[14]->GetYaxis()->SetTitle("TVR");
    TCanvas *cg15 = new TCanvas("cg15", "cg15", 0, 0, 800, 600);
    gr[15]->Draw("AP");
    gr[15]->GetXaxis()->SetTitle("Rise time (s)");
    gr[15]->GetYaxis()->SetTitle("Decay time (s)");
    TCanvas *cg13 = new TCanvas("cg13", "cg13", 0, 0, 800, 600);
    gr[13]->Draw("AP");
    gr[13]->GetYaxis()->SetTitle("Narrow correlation");
    TCanvas *cg7 = new TCanvas("cg7", "cg7", 0, 0, 800, 600);
    gr[7]->Draw("AP");
    gr[7]->GetYaxis()->SetTitle("Rise time (s)");
    TCanvas *cg8 = new TCanvas("cg8", "cg8", 0, 0, 800, 600);
    gr[8]->Draw("AP");
    gr[8]->GetYaxis()->SetTitle("Decay time (s)");
    TCanvas *cg16 = new TCanvas("cg16", "cg16", 0, 0, 800, 600);
    gr[16]->Draw("AP");
    gr[16]->GetXaxis()->SetTitle("Baseline (#muV)");
    gr[16]->GetYaxis()->SetTitle("Fitted baseline (#muV)");
    TCanvas *cg17 = new TCanvas("cg17", "cg17", 0, 0, 800, 600);
    gr[17]->Draw("AP");
    gr[17]->GetXaxis()->SetTitle("Baseline (ADC)");
    gr[17]->GetYaxis()->SetTitle("Filtered amp (ADC)");
    TCanvas *cg18 = new TCanvas("cg18", "cg18", 0, 0, 800, 600);
    gr[18]->Draw("AP");
    gr[18]->GetYaxis()->SetTitle("Fitted amp");
    TCanvas *cg19 = new TCanvas("cg19", "cg19", 0, 0, 800, 600);
    gr[19]->Draw("AP");
    gr[19]->GetYaxis()->SetTitle("Delayed amp");
    TCanvas *camp1 = new TCanvas("camp1", "", 0, 0, 800, 600);
    hamp1->Draw("");
    hamp1->GetXaxis()->SetTitle("Amplitude (#muV)");
    hamp1->GetYaxis()->SetTitle("Counts");
    hamp2->Draw("SAME");

    cout<<"Total number:\t"<<kgr[1]<<endl;
    cout<<"Keep number:\t"<<kgr[0]<<endl;
    cout<<"Ave amp:\t"<<ave_amp/kgr[0]<<endl;

}
