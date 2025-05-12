#include <TFile.h>
#include <TTree.h>
#include <TH2F.h>
#include <TCanvas.h>
#include <TColor.h>
#include <TStyle.h>
#include <iostream>

void draw_RiseTimeAmp() {
    // 打开ROOT文件
    TFile *file = TFile::Open("/Users/caohuaqi/Desktop/CUPID_China/Data_process/2505/SB2_2h_0506T1734/USTC-LD/data/TriggerEvent.root", "READ");
    if (!file || file->IsZombie()) {
        std::cerr << "Error: Could not open file or file is corrupted!" << std::endl;
        return;
    }

    // 获取TTree
    TTree *tree = (TTree*)file->Get("tree1");
    if (!tree) {
        std::cerr << "Error: Could not find the tree!" << std::endl;
        file->Close();
        return;
    }

    // 定义变量
    Float_t Amp_filtered;
    Long64_t RiseTime;
    Long64_t DecayTime;

    // 设置branch地址
    tree->SetBranchAddress("Amp_filtered", &Amp_filtered);
    tree->SetBranchAddress("RiseTime", &RiseTime);
    tree->SetBranchAddress("DecayTime", &DecayTime);

    // 创建二维直方图
    // 参数说明：名称，标题，x轴bin数，x轴下限，x轴上限，y轴bin数，y轴下限，y轴上限
    TH2F *hist2D = new TH2F("hist2D", "DecayTime vs Amp_filtered;Amp_filtered (ADC);DecayTime (sample points)",
                            500, 0, 1000000000,    // x轴: DecayTime 0-200ns, 100个bin
                            100, 0, 100);    // y轴: RiseTime 0-100ns, 100个bin

    // 设置颜色样式
    gStyle->SetPalette(kRainBow);  // 使用彩虹色系
    gStyle->SetOptStat(0);         // 不显示统计信息

    // 遍历树并填充直方图
    Long64_t nentries = tree->GetEntries();
    for (Long64_t i = 0; i < nentries; i++) {
        tree->GetEntry(i);
        if (RiseTime > 10 && DecayTime > 10 && Amp_filtered > 10000000) { // 应用限制条件
            hist2D->Fill(Amp_filtered, DecayTime);
        }
    }

    // 绘制二维直方图
    TCanvas *canvas = new TCanvas("canvas", "DecayTime vs Amp_filtered", 800, 600);
    hist2D->Draw("COLZ");  // "COLZ"表示用颜色表示z值，并显示颜色条

    // 保存图像
    //canvas->SaveAs("RiseDecayTime_2D.png");

    // 关闭文件
  //  file->Close();
}
