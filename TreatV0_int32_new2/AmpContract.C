#include <TFile.h>
#include <TTree.h>
#include <TH2F.h>
#include <TCanvas.h>
#include <iostream>

int drawAmpRT() {
   
    TFile *file = TFile::Open("TriggerEvent.root");
    if (!file || file->IsZombie()) {
        std::cerr << "Error: Could not open file TriggerEvent.root" << std::endl;
        return 1;
    }

 
    TTree *tree = (TTree*)file->Get("tree1"); //
    if (!tree) {
        std::cerr << "Error: Could not find TTree 'tree1' in the file" << std::endl;
        return 1;
    }

   
    Long64_t RiseTime;
    Double_t Amp_raw;

    // 定义二维直方图变量
    const Int_t nxBins = 120; // Amp_raw的bin数
    const Double_t xMin = 0.0; // Amp_raw的最小值
    const Double_t xMax = 120.0; // Amp_raw的最大值
    const Int_t nyBins = 120; // RiseTime的bin数
    const Double_t yMin = 0.0; // RiseTime的最小值
    const Double_t yMax = 120.0; // RiseTime的最大值
    TH2F *hAmpRise = new TH2F("hAmpRise", "Amp_raw vs RiseTime", nxBins, xMin, xMax, nyBins, yMin, yMax);

    // 遍历TTree并填充
    Long64_t nentries = tree->GetEntries();
    for (Long64_t i = 0; i < nentries; ++i) {
        // 设置两个分支的地址
        tree->SetBranchAddress("Amp_raw", &Amp_raw);
        tree->SetBranchAddress("RiseTime", &RiseTime);
        // 读取当前条目
        tree->GetEntry(i);

        
        hAmpRise->Fill(Amp_raw, RiseTime);
    }

    // 检查二维直方图是否填充了数据
    if (hAmpRise->GetEntries() == 0) {
        std::cerr << "Warning: Histogram 'hAmpRise' is empty. No data was filled." << std::endl;
    }

  
    TCanvas *c1 = new TCanvas("c1", "Amp_raw vs RiseTime", 800, 600);
    hAmpRise->SetTitle("Amp_raw vs RiseTime Distribution");
    hAmpRise->GetXaxis()->SetTitle("Amp_raw");
    hAmpRise->GetYaxis()->SetTitle("RiseTime");
    hAmpRise->Draw("COLZ");

    return 0;
}

int main() {
    return drawAmpRT();
}
