#include <TFile.h>
#include <TTree.h>
#include <TH2F.h>
#include <TCanvas.h>
#include <TColor.h>
#include <TStyle.h>
#include <iostream>

void Ana_Rain_Bow()
{
    // 打开ROOT文件
    TFile *file = TFile::Open("/Users/caohuaqi/Desktop/CUPID_China/Data_process/2505/SB2_2h_0506T1734/USTC-LD/data/TriggerEvent.root", "READ");
    if (!file || file->IsZombie())
    {
        std::cerr << "Error: Could not open file or file is corrupted!" << std::endl;
        return;
    }

    // 获取TTree
    TTree *tree = (TTree *)file->Get("tree1");
    if (!tree)
    {
        std::cerr << "Error: Could not find the tree!" << std::endl;
        file->Close();
        return;
    }

    // 定义变量
    Float_t Amp_filtered;
    Long64_t RiseTime, DecayTime;
    Double_t Amp_raw;

    // 设置branch地址
    tree->SetBranchAddress("Amp_filtered", &Amp_filtered);
    tree->SetBranchAddress("Amp_raw", &Amp_raw); 
    tree->SetBranchAddress("RiseTime", &RiseTime);
    tree->SetBranchAddress("DecayTime", &DecayTime);

    // 设置颜色样式
    gStyle->SetPalette(kRainBow);
    gStyle->SetOptStat(0);

    // 创建四个二维直方图
    TH2F *h1 = new TH2F("h1", "DecayTime vs Amp_filtered;Amp_filtered (ADC);DecayTime (sample points)",
                        500, 0, 1e8, 100, 0, 100);

    TH2F *h2 = new TH2F("h2", "DecayTime vs RiseTime;RiseTime (sample points);DecayTime (sample points)",
                        100, 0, 100, 100, 0, 100);

    TH2F *h3 = new TH2F("h3", "RiseTime vs Amp_filtered;Amp_filtered (ADC);RiseTime (sample points)",
                        500, 0, 1e8, 100, 0, 100);

    TH2F *h4 = new TH2F("h4", "Amp_raw vs Amp_filtered;Amp_filtered (ADC);Amp_raw (ADC)",
                        500, 0, 1e8, 500, 0, 1e8);

    // 遍历树并填充直方图
    Long64_t nentries = tree->GetEntries();
    for (Long64_t i = 0; i < nentries; i++)
    {
        tree->GetEntry(i);
        if (RiseTime > 10 && DecayTime > 10 && Amp_filtered > 1e7)
        {
            h1->Fill(Amp_filtered, DecayTime);
            h2->Fill(RiseTime, DecayTime);
            h3->Fill(Amp_filtered, RiseTime);
            h4->Fill(Amp_filtered, Amp_raw);
        }
    }

    // 创建画布并绘图
    TCanvas *c1 = new TCanvas("c1", "DecayTime vs Amp_filtered", 800, 600);
    h1->Draw("COLZ");
    // c1->SaveAs("DecayTime_vs_Amp_filtered.png");

    TCanvas *c2 = new TCanvas("c2", "DecayTime vs RiseTime", 800, 600);
    h2->Draw("COLZ");
    // c2->SaveAs("DecayTime_vs_RiseTime.png");

    TCanvas *c3 = new TCanvas("c3", "RiseTime vs Amp_filtered", 800, 600);
    h3->Draw("COLZ");
    // c3->SaveAs("RiseTime_vs_Amp_filtered.png");

    TCanvas *c4 = new TCanvas("c4", "Amp_raw vs Amp_filtered", 800, 600);
    h4->Draw("COLZ");
    // c4->SaveAs("Amp_raw_vs_Amp_filtered.png");

}
