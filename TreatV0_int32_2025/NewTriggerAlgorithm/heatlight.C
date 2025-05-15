#include<iostream>
#include "TTree.h"
#include "TFile.h"
#include "TString.h"
#include <fstream>
using namespace std;


void heatlight(TString heat_file = "./data/heat2.root", TString light_file = "./data/light2.root")
{


    //fs: sampling frequency;
    Int_t fs = 5000;
    //sb: bytes number for each data
    Int_t sb = 4;
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
    std::string branches[] = {"trigpos","rawamp","filamp","baseline","baselineRMS","correlation","tv","tvl","tvr","SI","baseline_slope","fitted_baseline","fitted_rawamp","risetime","decaytime","delayamp","meantime","rawarea","filarea","correlation_narrow"};

    TFile *infile_h = new TFile(heat_file);
    TTree *t1_heat  = (TTree*)infile_h->Get("tree1");
    TFile *infile_l = new TFile(light_file);
    TTree *t1_light = (TTree*)infile_l->Get("tree1");

    Double_t entries_h[19] = {0.0};
    Double_t entries_l[19] = {0.0};
    const int float_entries = 19;

    Long64_t time_h = 0;
    Long64_t time_l = 0;
    t1_heat->SetBranchAddress(branches[0].c_str(), &time_h);
    t1_light->SetBranchAddress(branches[0].c_str(), &time_l);
    for(int i=0; i < float_entries; i++){
        t1_heat->SetBranchAddress(branches[i+1].c_str(), &entries_h[i]);
        t1_light->SetBranchAddress(branches[i+1].c_str(), &entries_l[i]);
    }

    TGraph *gr_HL = new TGraph();
    TGraph *gr_LY = new TGraph();
    gr_HL->SetMarkerColor(kBlue);
    gr_LY->SetMarkerColor(kBlue);

    TGraph *gr[20];
    for(int i=0; i < 20; i++){
        gr[i] = new TGraph();
        gr[i]->GetXaxis()->SetTitle("Filtered amp (#muV)");
        gr[i]->SetMarkerStyle(7);
        gr[i]->SetMarkerColor(kBlue);
    }
    gr[0]->SetMarkerColor(kRed);
    Int_t kgr[10] = {0};
    cout<<"Triggered number:\t"<<t1_heat->GetEntries()<<endl;
    cout<<"Triggered number:\t"<<t1_light->GetEntries()<<endl;
    Int_t Num = t1_heat->GetEntries();
    if(Num!=t1_light->GetEntries()){
        throw std::invalid_argument( "The events number of heat and light are not matched!" );
    }
    Int_t tmp_pos = 0;
    Int_t Time = 0;
    Float_t new_amp = 0.0;
    Float_t ave_amp = 0.0;
    Float_t ene_h, ene_l = 0.0;

    const Int_t Nbin = 560;
    //TH1::SetDefaultSumw2();
    TH1D *hamp1 = new TH1D("hamp1"," ;Amplitude;Counts", Nbin,0,280000);
    TH1D *hamp2 = new TH1D("hamp2"," ;Amplitude;Counts", Nbin,0,280000);
    TH1D *hamp3 = new TH1D("hamp3"," ;Amplitude;Counts", Nbin,0,280000);
    //TH1D *histo_ly = new TH1D("histo_hly"," ;Light yield (keV/MeV);Counts",140,-0.2,0.5);
    TH1D *histo_ly = new TH1D("histo_hly"," ;Light yield (keV/MeV);Counts",140,-10,10);
    TH1D *histo_betagamma = new TH1D("histo_betagamma"," ;Light yield (keV/MeV);Counts",200,-10,10);
    TH1D *histo_alpha = new TH1D("histo_alpha"," ;Light yield (keV/MeV);Counts",200,-10,10);
    Int_t kkk = 0;



    for(int i=0; i < Num; i++){
        t1_heat->GetEntry(i);
        t1_light->GetEntry(i);
        /*
           if(time_h<tmp_pos){
           Time += tmp_pos;
           }
           tmp_pos = time_h;
           */
        kgr[1] += 1;
        //if(entries[3] > 300)continue;
        //if(entries_h[4] < 0.995)continue;
        //if(entries_l[4] < 0.2)continue;
        //if(entries[1] > 2.3E5)continue;
        kgr[0] += 1;
        if(entries_h[2]<-380000){
            new_amp = entries_h[1]*201681*(1.0/(entries_h[2]*-0.0208395+190002));
        }
        else{
            new_amp = entries_h[1]*201681*(1.0/(entries_h[2]*-0.0188948+191259));
        }
        new_amp = entries_h[1]*1460/2029.94;
        //new_amp = entries_h[1]*2614/(96706.5-0.036539*entries_h[0]-1.58e-9*entries_h[0]*entries_h[0]);

        gr[1]->SetPoint(kgr[0], (time_h)/fs/3600., entries_l[2]);
        gr[2]->SetPoint(kgr[0], (time_h)/fs/3600., entries_l[3]);
        //gr[3]->SetPoint(kgr[0], entries_h[1], entries_h[4]);
        gr[3]->SetPoint(kgr[0], entries_l[1], entries_l[4]);
        gr[4]->SetPoint(kgr[0], entries_h[1], entries_h[5]);
        gr[5]->SetPoint(kgr[0], entries_h[1], 1000*entries_h[6]);
        gr[6]->SetPoint(kgr[0], entries_h[1], 1000*entries_h[7]);
        gr[7]->SetPoint(kgr[0], entries_h[1], entries_h[10]);
        gr[8]->SetPoint(kgr[0], entries_h[1], entries_h[11]);
        gr[9]->SetPoint(kgr[0],  new_amp, entries_h[12]/entries_h[1]);
        gr[10]->SetPoint(kgr[0], new_amp, entries_h[13]/entries_h[1]);
        gr[11]->SetPoint(kgr[0], new_amp, entries_h[14]/entries_h[1]);
        gr[12]->SetPoint(kgr[0], new_amp, entries_h[15]/entries_h[1]);
        gr[13]->SetPoint(kgr[0], entries_h[1], entries_h[16]);
        gr[14]->SetPoint(kgr[0], 1000*entries_h[6], 1000*entries_h[7]);
        gr[15]->SetPoint(kgr[0], entries_h[10], entries_h[11]);
        gr[16]->SetPoint(kgr[0], entries_h[2], entries_h[9]);
        gr[17]->SetPoint(kgr[0], entries_h[2], entries_h[1]);
        gr[18]->SetPoint(kgr[0], new_amp, entries_h[8]/entries_h[1]);
        gr[19]->SetPoint(kgr[0], new_amp, entries_h[12]/entries_h[1]);
        hamp1->Fill(entries_h[1]);
        hamp2->Fill(entries_h[0]-entries_h[2]);
        hamp3->Fill(entries_h[8]);
        ene_h = new_amp;//entries_h[1];
                        //ene = new_amp*1.00843e-02+new_amp*new_amp*-2.17879e-10;
        if(ene_h < 0)continue;
        kkk += 1;
        ene_l = entries_l[1]*100.6/430.12;
        gr_HL->SetPoint(kkk, ene_h, ene_l);
        gr_LY->SetPoint(kkk, ene_h, 1000*ene_l/ene_h);
        if(entries_h[4]<0.994)continue;
        //if(ene_h > 2000)histo_ly->Fill(1000*ene_l/ene_h);
        if(ene_h < 1000)continue;
        if(ene_h < 2700)histo_betagamma->Fill(1000*ene_l/ene_h);
        if(ene_h > 4000)histo_alpha->Fill(1000*ene_l/ene_h);
        if (ene_h <5000-20)continue;
        if (ene_l < 0.2)continue;
        //if (ene_h >2614+20)continue;
        //cout<<time_h<<endl;
        //cout<<time_l<<endl;
        ave_amp += entries_l[1];
        kgr[4]+=1;
    } 
    cout<<"Total number:\t"<<kgr[1]<<endl;
    cout<<"Keep number:\t"<<kgr[0]<<endl;
    cout<<"Ave amp:\t"<<ave_amp/kgr[4]<<endl;
    TCanvas *cg3 = new TCanvas("cg3", "cg3", 0, 0, 800, 600);
    gr[3]->Draw("AP");
    gr[3]->GetYaxis()->SetTitle("Correlation");
    TCanvas *cg1 = new TCanvas("cg1", "cg1", 0, 0, 800, 600);
    gr[1]->Draw("AP");
    gr[1]->GetXaxis()->SetTitle("Time (hour)");
    gr[1]->GetYaxis()->SetTitle("Baseline (#muV)");
    //gr[0]->Draw("P SAME");
    TCanvas *cg2 = new TCanvas("cg2", "cg2", 0, 0, 800, 600);
    gr[2]->Draw("AP");
    gr[2]->GetXaxis()->SetTitle("Time (hour)");
    gr[2]->GetYaxis()->SetTitle("Baseline RMS (#muV)");
    /*
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
    //gr[15]->GetXaxis()->SetTitle("Correlation");
    gr[15]->GetXaxis()->SetTitle("Rise time (s)");
    gr[15]->GetYaxis()->SetTitle("Decay time (s)");
    TCanvas *cg13 = new TCanvas("cg13", "cg13", 0, 0, 800, 600);
    gr[13]->Draw("AP");
    gr[13]->GetYaxis()->SetTitle("#chi{^2} raw");
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
    gr[17]->GetXaxis()->SetTitle("Baseline (#muV)");
    gr[17]->GetYaxis()->SetTitle("Filtered amp (#muV)");
    TCanvas *cg18 = new TCanvas("cg18", "cg18", 0, 0, 800, 600);
    gr[18]->Draw("AP");
    gr[18]->GetYaxis()->SetTitle("Fitted amp");
    TCanvas *cg19 = new TCanvas("cg19", "cg19", 0, 0, 800, 600);
    gr[19]->Draw("AP");
    gr[19]->GetYaxis()->SetTitle("Delayed amp");
    */
    /*
    */
    /*
       TCanvas *camp1 = new TCanvas("camp1", "", 0, 0, 800, 600);
       hamp1->Draw("HIST");
       hamp1->GetXaxis()->SetTitle("Amplitude (#muV)");
       hamp1->GetYaxis()->SetTitle("Counts");
       hamp2->Draw("SAME");
       */

    TCanvas *cg_HL = new TCanvas("cgHL", "cgHL", 0, 0, 800, 600);
    gr_HL->Draw("AP");
    gr_HL->GetXaxis()->SetTitle("Heat (keV)");
    gr_HL->GetYaxis()->SetTitle("Light (keV)");
    gr_HL->SetMarkerStyle(7);
    gr_HL->SetMarkerColor(kBlue);
    TCanvas *cg_LY = new TCanvas("cg_LY", "cg_LY", 0, 0, 800, 600);
    gr_LY->Draw("AP");
    gr_LY->GetXaxis()->SetTitle("Heat (keV)");
    gr_LY->GetYaxis()->SetTitle("Light yield (keV/MeV)");
    gr_LY->GetXaxis()->SetRangeUser(0,8000);
    //gr_LY->GetYaxis()->SetRangeUser(-1,2);

    TF1 *fgaus = new TF1("fgaus","gaus(0)+gaus(3)",-0.2,0.6);
    fgaus->SetParameters(10,0.05,0.01,100,0.2,0.2);

    TCanvas *cg_LYre = new TCanvas("cg_LYre", "cg_LYre", 0, 0, 800, 600);
    histo_alpha->Draw("");
    histo_betagamma->Draw("SAME");
    /*
       histo_ly->Draw();
       histo_ly->Fit("fgaus");
       Double_t paras[6] = {0.0};
    //Double_t paras_err[6] = {0.0};
    //fgaus->GetParErrors(paras_err);
    fgaus->GetParameters(paras);
    Double_t dp = (paras[4]-paras[1])/TMath::Sqrt(paras[2]*paras[2]+paras[5]*paras[5]);
    TPaveText *pt = new TPaveText(.15,.7,0.35,0.9,"TL NDC");
    pt->AddText(Form("DP=%.4f",dp));
    pt->AddText(Form("LY_{#alpha}=%.4f #pm %.4f",paras[1],paras[2]));
    pt->AddText(Form("LY_{#beta/#gamma}=%.4f #pm %.4f",paras[4],paras[5]));

    pt->Draw("same");
    */

}
