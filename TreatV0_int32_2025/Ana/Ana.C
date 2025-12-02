#include <fstream>
#include <iostream>
#include <TStyle.h>
#include <string>

#include "TCanvas.h"
#include "TF1.h"
#include "TTree.h"
#include "TFile.h"
#include "TMath.h"
#include "TGraph.h"
#include "TSpectrum.h"
#include "TLegend.h"
#include "TSystem.h"

// 需要 ROOT GUI 头文件来弹出文件选择对话框
#include "TGClient.h"
#include "TGFileDialog.h"

#include <iomanip>
using namespace TMath;

void Ana() {
    //========================
    // 1. 弹框选择输入 ROOT 文件
    //========================
    static const char *filetypes[] = {
        "ROOT files", "*.root",
        0,            0
    };

    TGFileInfo fi;
    fi.fFileTypes = filetypes;
    fi.fIniDir    = StrDup(gSystem->pwd()); // 初始目录为当前工作目录

    new TGFileDialog(gClient->GetRoot(), 0, kFDOpen, &fi);
    if (!fi.fFilename) {
        std::cout << "未选择输入文件，退出。" << std::endl;
        return;
    }

    TString inFileName = fi.fFilename;
    std::cout << "选择的输入文件: " << inFileName << std::endl;

    // 输入文件所在目录
    TString inDir = gSystem->DirName(inFileName);
    // 在该目录下新建 Ana 目录
    TString outDir = inDir + "/Ana";
    if (gSystem->MakeDirectory(outDir) == 0) {
        std::cout << "输出目录: " << outDir << std::endl;
    } else {
        std::cout << "注意：目录 " << outDir << " 可能已存在或创建失败。(若已存在可忽略)" << std::endl;
    }

    //========================
    // 2. 打开输入 ROOT 文件
    //========================
    TFile *f1 = TFile::Open(inFileName, "READ");
    if (!f1 || f1->IsZombie()) {
        std::cout << "无法打开输入文件: " << inFileName << std::endl;
        return;
    }

    TTree *T1 = (TTree*) f1->Get("tree1");
    if (!T1) {
        std::cout << "在文件中未找到 TTree 'tree1'，退出。" << std::endl;
        f1->Close();
        return;
    }

    //========================
    // 3. 原来的变量与分支设置
    //========================
    Long64_t        MaxPos;
    Double_t        Baseline;
    Double_t        Amp_raw;
    Float_t         Amp_filtered;
    Long64_t        RiseTime;
    Long64_t        DecayTime;
    Double_t        TVL;
    Double_t        TVR;
    Double_t        Chi2raw;
    Double_t        Chi2filtered;
    Double_t        amp_rawfit;
    Double_t        bl_rawfit;
    Double_t        lstsq_rawfit;
    Double_t        amp_filterfit;
    Double_t        bl_filterfit;
    Double_t        lstsq_filterfit;
    Double_t        bl_RMS;
    Double_t        bl_slope;
    Double_t        bl_chi2;

    T1->SetBranchAddress("MaxPos", &MaxPos);
    T1->SetBranchAddress("Baseline", &Baseline);
    T1->SetBranchAddress("Amp_raw", &Amp_raw);
    T1->SetBranchAddress("Amp_filtered", &Amp_filtered);
    T1->SetBranchAddress("RiseTime", &RiseTime);
    T1->SetBranchAddress("DecayTime", &DecayTime);
    T1->SetBranchAddress("TVL", &TVL);
    T1->SetBranchAddress("TVR", &TVR);
    T1->SetBranchAddress("Chi2raw", &Chi2raw);
    T1->SetBranchAddress("Chi2filtered", &Chi2filtered);
    T1->SetBranchAddress("amp_rawfit", &amp_rawfit);
    T1->SetBranchAddress("bl_rawfit", &bl_rawfit);
    T1->SetBranchAddress("lstsq_rawfit", &lstsq_rawfit);
    T1->SetBranchAddress("amp_filterfit", &amp_filterfit);
    T1->SetBranchAddress("bl_filterfit", &bl_filterfit);
    T1->SetBranchAddress("lstsq_filterfit", &lstsq_filterfit);
    T1->SetBranchAddress("bl_RMS", &bl_RMS);
    T1->SetBranchAddress("bl_slope", &bl_slope);
    T1->SetBranchAddress("bl_chi2", &bl_chi2);

    Long64_t nbytes = T1->GetEntry(0);
    (void)nbytes;
    std::cout << "第一个事件的Amp_filtered: " << Amp_filtered << std::endl;

    //========================
    // 4. 输出 ROOT 文件 & 直方图
    //========================
    TString resultRootName = outDir + "/result.root";
    TFile *f2 = new TFile(resultRootName, "RECREATE");

    TH1D *hamp1 = new TH1D("hamp1"," ;Amplitude;Counts", 30000,0,300000000);
    TH1D *hamp2 = new TH1D("hamp2"," ;Amplitude;Counts", 30000,0,300000000);
    TH1D *hamp3 = new TH1D("hamp3"," ;Amplitude;Counts", 30000,0,300000000);
    TH1D *hamp4 = new TH1D("hamp4"," ;Amplitude;Counts", 30000,0,300000000);
    TH1D *hamp5 = new TH1D("hamp5"," ;Amplitude;Counts", 30000,0,300000000);

    // ★关键：解绑直方图与当前 TFile，避免 f2->Close() 时被删除
    hamp1->SetDirectory(nullptr);
    hamp2->SetDirectory(nullptr);
    hamp3->SetDirectory(nullptr);
    hamp4->SetDirectory(nullptr);
    hamp5->SetDirectory(nullptr);

    TGraph *g1 = new TGraph();
    TGraph *g2 = new TGraph();
    TGraph *g3 = new TGraph();
    TGraph *g4 = new TGraph();
    TGraph *g5 = new TGraph();
    TGraph *g6 = new TGraph();
    TGraph *g7 = new TGraph();
    TGraph *g8 = new TGraph();
    TGraph *g9 = new TGraph();

    int k1 = 0;

    //========================
    // 5. cut.root 和 tcut
    //========================
    TString cutRootName = outDir + "/cut.root";
    TFile *fcut = new TFile(cutRootName, "RECREATE");
    TTree *tcut = T1->CloneTree(0);
    Double_t ene = 0.0;
    tcut->Branch("ene",&ene,"ene/D");

    int n = T1->GetEntries();
    double coeff = 1.0;

    //========================
    // 6. 输出 txt：triggered_events.txt
    //========================
    TString txtName = outDir + "/triggered_events.txt";
    std::ofstream outfile;
    outfile.open(txtName.Data(), std::ios_base::out);
    std::cout.setf(std::ios::fixed);

    //========================
    // 7. Loop 事件
    //========================
    for(int i = 0; i < n; i++) {
        T1->GetEntry(i);

        if (Amp_raw < 0) continue;
        if (Amp_filtered < 0.0) continue;
        if (amp_filterfit < 0) continue;
        if (amp_rawfit < 0) continue;
        if (DecayTime < 10) continue;

        ene = amp_filterfit * Amp_filtered;

        g1->SetPoint(k1, Baseline, amp_filterfit*Amp_filtered);
        g2->SetPoint(k1, MaxPos/3600./10000., Baseline);
        g3->SetPoint(k1, RiseTime, DecayTime);
        g4->SetPoint(k1, lstsq_rawfit, lstsq_filterfit);
        g5->SetPoint(k1, amp_rawfit, amp_filterfit);
        g6->SetPoint(k1, Chi2filtered, TVL);
        g7->SetPoint(k1, Chi2filtered, TVR);
        g8->SetPoint(k1, amp_filterfit*Amp_filtered, Chi2filtered);
        g9->SetPoint(k1, Amp_filtered, DecayTime);

        hamp1->Fill(Amp_raw/coeff);
        hamp2->Fill(amp_rawfit/coeff);
        hamp3->Fill(Amp_filtered/coeff);
        hamp4->Fill(Amp_filtered*amp_filterfit/coeff);
        hamp5->Fill(amp_rawfit/coeff);

        tcut->Fill();

        outfile << std::setprecision(10)
                << MaxPos/10000. + 0.5 << ","
                << Amp_filtered*amp_filterfit/coeff << ","
                << Amp_raw/coeff << std::endl;

        k1++;
    }

    outfile.close();
    std::cout << "Total triggered:\t" << k1 << std::endl;

    // 写 cut.root
    fcut->cd();
    tcut->Write();
    fcut->Close();

    //========================
    // 8. 画图 + 保存 PNG（使用具体名称）
    //========================
    gStyle->SetOptStat(0);

    // 1) Baseline vs Amplitude
    TCanvas *cBaselineVsAmplitude = new TCanvas("cBaselineVsAmplitude",
                                                "Baseline vs Amplitude",
                                                0, 0, 800, 600);
    cBaselineVsAmplitude->cd();
    g1->SetMarkerColor(kRed);
    g1->Draw("AP");
    g1->GetXaxis()->SetTitle("Baseline");
    g1->GetYaxis()->SetTitle("Amplitude");
    cBaselineVsAmplitude->Update();
    cBaselineVsAmplitude->SaveAs((outDir + "/cBaselineVsAmplitude.png").Data());

    // 2) Time vs Baseline
    TCanvas *cTimeVsBaseline = new TCanvas("cTimeVsBaseline",
                                           "Time vs Baseline",
                                           0, 0, 800, 600);
    cTimeVsBaseline->cd();
    g2->SetMarkerColor(kBlue);
    g2->Draw("AP");
    g2->GetXaxis()->SetTitle("Time (h)");
    g2->GetYaxis()->SetTitle("Baseline");
    cTimeVsBaseline->Update();
    cTimeVsBaseline->SaveAs((outDir + "/cTimeVsBaseline.png").Data());

    // 3) RiseTime vs DecayTime
    TCanvas *cRiseTimeVsDecayTime = new TCanvas("cRiseTimeVsDecayTime",
                                                "RiseTime vs DecayTime",
                                                0, 0, 800, 600);
    cRiseTimeVsDecayTime->cd();
    g3->SetMarkerColor(kGreen);
    g3->Draw("AP");
    g3->GetXaxis()->SetTitle("RiseTime");
    g3->GetYaxis()->SetTitle("DecayTime");
    cRiseTimeVsDecayTime->Update();
    cRiseTimeVsDecayTime->SaveAs((outDir + "/cRiseTimeVsDecayTime.png").Data());

    // 4) Lstsq_rawfit vs Lstsq_filterfit（轴标题还是沿用你原来写的 chi2_xxx）
    TCanvas *cLstsqRawfitVsLstsqFilterfit =
        new TCanvas("cLstsqRawfitVsLstsqFilterfit",
                    "Lstsq_rawfit vs Lstsq_filterfit",
                    0, 0, 800, 600);
    cLstsqRawfitVsLstsqFilterfit->cd();
    g4->SetMarkerColor(kRed);
    g4->Draw("AP");
    g4->GetXaxis()->SetTitle("chi2_rawfit");
    g4->GetYaxis()->SetTitle("chi2_filterfit");
    cLstsqRawfitVsLstsqFilterfit->Update();
    cLstsqRawfitVsLstsqFilterfit
        ->SaveAs((outDir + "/cLstsqRawfitVsLstsqFilterfit.png").Data());

    // 5) Amp_rawfit vs Amp_filterfit
    TCanvas *cAmpRawfitVsAmpFilterfit =
        new TCanvas("cAmpRawfitVsAmpFilterfit",
                    "Amp_rawfit vs Amp_filterfit",
                    0, 0, 800, 600);
    cAmpRawfitVsAmpFilterfit->cd();
    g5->SetMarkerColor(kRed);
    g5->Draw("AP");
    g5->GetXaxis()->SetTitle("Amp_rawfit");
    g5->GetYaxis()->SetTitle("Amp_filterfit");
    cAmpRawfitVsAmpFilterfit->Update();
    cAmpRawfitVsAmpFilterfit
        ->SaveAs((outDir + "/cAmpRawfitVsAmpFilterfit.png").Data());

    // 6) Chi2filtered vs TVL
    TCanvas *cChi2filteredVsTVL = new TCanvas("cChi2filteredVsTVL",
                                              "Chi2filtered vs TVL",
                                              0, 0, 800, 600);
    cChi2filteredVsTVL->cd();
    g6->SetMarkerColor(kRed);
    g6->Draw("AP");
    g6->GetXaxis()->SetTitle("chi2_filtered");
    g6->GetYaxis()->SetTitle("TVL");
    cChi2filteredVsTVL->Update();
    cChi2filteredVsTVL->SaveAs((outDir + "/cChi2filteredVsTVL.png").Data());

    // 7) Chi2filtered vs TVR
    TCanvas *cChi2filteredVsTVR = new TCanvas("cChi2filteredVsTVR",
                                              "Chi2filtered vs TVR",
                                              0, 0, 800, 600);
    cChi2filteredVsTVR->cd();
    g7->SetMarkerColor(kRed);
    g7->Draw("AP");
    g7->GetXaxis()->SetTitle("chi2_filtered");
    g7->GetYaxis()->SetTitle("TVR");
    cChi2filteredVsTVR->Update();
    cChi2filteredVsTVR->SaveAs((outDir + "/cChi2filteredVsTVR.png").Data());

    // 8) Amplitude vs Chi2filtered
    TCanvas *cAmplitudeVsChi2filtered =
        new TCanvas("cAmplitudeVsChi2filtered",
                    "Amplitude vs Chi2filtered",
                    0, 0, 800, 600);
    cAmplitudeVsChi2filtered->cd();
    g8->SetMarkerColor(kRed);
    g8->Draw("AP");
    g8->GetXaxis()->SetTitle("Amplitude");
    g8->GetYaxis()->SetTitle("Chi2Filtered");
    cAmplitudeVsChi2filtered->Update();
    cAmplitudeVsChi2filtered
        ->SaveAs((outDir + "/cAmplitudeVsChi2filtered.png").Data());

    // 9) Amplitude vs DecayTime
    TCanvas *cAmplitudeVsDecayTime =
        new TCanvas("cAmplitudeVsDecayTime",
                    "Amplitude vs DecayTime",
                    0, 0, 800, 600);
    cAmplitudeVsDecayTime->cd();
    g9->SetMarkerColor(kRed);
    g9->Draw("AP");
    g9->GetXaxis()->SetTitle("Amplitude");
    g9->GetYaxis()->SetTitle("Decay Time");
    cAmplitudeVsDecayTime->Update();
    cAmplitudeVsDecayTime
        ->SaveAs((outDir + "/cAmplitudeVsDecayTime.png").Data());

    // 10) Amplitude Spectrum (hamp1, hamp2, hamp3)
    TCanvas *cAmplitudeSpectrum =
        new TCanvas("cAmplitudeSpectrum",
                    "Amplitude Spectrum",
                    0, 0, 800, 600);
    cAmplitudeSpectrum->cd();
    hamp1->Draw("HIST");
    hamp2->Draw("HIST SAME");
    hamp3->Draw("HIST SAME");

    hamp1->SetLineColor(kBlack);
    hamp2->SetLineColor(kBlue);
    hamp3->SetLineColor(kRed);

    hamp1->GetXaxis()->SetTitle("Energy (ADC)");
    hamp1->GetYaxis()->SetTitle("Counts");

    TLegend *leg1 = new TLegend(0.55,0.65,0.76,0.82);
    leg1->AddEntry(hamp1,"Raw","l");
    leg1->AddEntry(hamp2,"Raw_fit","l");
    leg1->AddEntry(hamp3,"Filtered","l");
    leg1->Draw();

    cAmplitudeSpectrum->Update();
    cAmplitudeSpectrum
        ->SaveAs((outDir + "/cAmplitudeSpectrum.png").Data());

    //========================
    // 9. 写 result.root
    //========================
    f2->cd();
    hamp1->Write();
    hamp2->Write();
    hamp3->Write();
    hamp4->Write();
    hamp5->Write();
    f2->Close();

    // 关闭输入文件
    f1->Close();

    std::cout << "所有输出已保存到目录：" << outDir << std::endl;
}