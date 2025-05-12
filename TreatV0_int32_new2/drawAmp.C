#include <TFile.h>
#include <TTree.h>
#include <TH2F.h>
#include <TCanvas.h>
#include <iostream>

int drawAmp() {
    TFile *file = TFile::Open("TriggerEvent.root");
    if (!file || file->IsZombie()) {
        std::cerr << "Error: Could not open file TriggerEvent.root" << std::endl;
        return 1;
    }

    // 获取TTree对象
    TTree *tree = (TTree*)file->Get("tree1");
    if (!tree) {
        std::cerr << "Error: Could not find TTree 'tree1' in the file" << std::endl;
        return 1;
    }

    // 定义变量来存储Amp_raw和Amp_filtered的值
    Double_t Amp_raw; // Amp_raw浮点数
    Float_t Amp_filtered; // Amp_filtered浮点数

    // 定义二维直方图变量
    const Int_t nxBins = 2000; // Amp_raw的bin数
    const Double_t xMin = 0.0; // Amp_raw的最小值
    const Double_t xMax = 2000.0; // Amp_raw的最大值
    const Int_t nyBins = 2000; // Amp_filtered的bin数
    const Double_t yMin = 0.0; // Amp_filtered的最小值
    const Double_t yMax = 2000.0; // Amp_filtered的最大值
    TH2F *hAmpRawFiltered = new TH2F("hAmpRawFiltered", "Amp_raw vs Amp_filtered", nxBins, xMin, xMax, nyBins, yMin, yMax);

    // 遍历TTree并填充
    Long64_t nentries = tree->GetEntries();
    for (Long64_t i = 0; i < nentries; ++i) {
        // 设置两个分支的地址
        tree->SetBranchAddress("Amp_raw", &Amp_raw);
        tree->SetBranchAddress("Amp_filtered", &Amp_filtered);
       
        tree->GetEntry(i);

        hAmpRawFiltered->Fill(Amp_raw, Amp_filtered);
    }

    // 检查是否填充了数据
    if (hAmpRawFiltered->GetEntries() == 0) {
        std::cerr << "Warning: Histogram 'hAmpRawFiltered' is empty. No data was filled." << std::endl;
    }

    TCanvas *c1 = new TCanvas("c1", "Amp_raw vs Amp_filtered", 800, 600);
    hAmpRawFiltered->SetTitle("Amp_raw vs Amp_filtered Distribution");
    hAmpRawFiltered->GetXaxis()->SetTitle("Amp_raw");
    hAmpRawFiltered->GetYaxis()->SetTitle("Amp_filtered");
    hAmpRawFiltered->Draw("COLZ"); 

    return 0;
}

int main() {
    return drawAmp();
}
