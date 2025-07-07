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
#include <iomanip>
using namespace TMath;
void Ana()
{
	Long64_t MaxPos;
	Double_t Baseline;
	Double_t Amp_raw;
	Float_t Amp_filtered;
	Long64_t RiseTime;
	Long64_t DecayTime;
	Double_t TVL;
	Double_t TVR;
	Double_t Chi2raw;
	Double_t Chi2filtered;
	Double_t amp_rawfit;
	Double_t bl_rawfit;
	Double_t lstsq_rawfit;
	Double_t amp_filterfit;
	Double_t bl_filterfit;
	Double_t lstsq_filterfit;
	Double_t bl_RMS;
	Double_t bl_slope;
	Double_t bl_chi2;
	TFile *f1 = new TFile("/Users/caohuaqi/Desktop/CUPID_China/Data_process/2504/BKG_SB2_4H_0421T0953/DLMO_narrow/data/TriggerEvent.root", "READ");

	TTree *T1 = (TTree *)f1->Get("tree1");

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

	TFile *f2 = new TFile("/Users/caohuaqi/Workspace/Backup/TreatV0_int32_2025/Ana/result.root", "RECREATE");
	TH1D *hamp1 = new TH1D("hamp1", " ;Amplitude;Counts", 3600, 0, 120);
	TH1D *hamp2 = new TH1D("hamp2", " ;Amplitude;Counts", 3600, 0, 120);
	TH1D *hamp3 = new TH1D("hamp3", " ;Amplitude;Counts", 3600, 0, 120);
	TH1D *hamp4 = new TH1D("hamp4", " ;Amplitude;Counts", 3600, 0, 120);
	TH1D *hamp5 = new TH1D("hamp5", " ;Amplitude;Counts", 3600, 0, 120);

	TGraph *g1 = new TGraph();
	TGraph *g2 = new TGraph();
	TGraph *g3 = new TGraph();
	TGraph *g4 = new TGraph();
	TGraph *g5 = new TGraph();
	TGraph *g6 = new TGraph();
	TGraph *g7 = new TGraph();
	TGraph *g8 = new TGraph();
	TGraph *g9 = new TGraph();

	int k1, k2, k3, k4, k5, k6, k7, k8;
	k1 = 0;
	k2 = 0;
	k3 = 0;
	k4 = 0;
	k5 = 0;
	k6 = 0;
	// T1.SetBranchStatus("*",0);
	// T1.SetBranchStatus("c",1);
	// T1.setBranchStatus("e",1);

	TFile *fcut = new TFile("/Users/caohuaqi/Workspace/Backup/TreatV0_int32_2025/Ana/cut.root", "RECREATE");
	TTree *tcut = T1->CloneTree(0);
	Double_t ene = 0.0;
	tcut->Branch("ene", &ene, "ene/D");
	int n = T1->GetEntries();
	double coeff = 1.0; //(TMath::Power(2,16)-1)*0.01;
	ofstream outfile;
	outfile.open("./triggered_events.txt", ios_base::out);
	cout.setf(ios::fixed);
	for (int i = 0; i < n; i++)
	{
		T1->GetEntry(i);
		// if(vbias_rms > 0.01)continue;
		// if(Bl_RMS > 0.0035)continue;
		// if(Baseline > 0.5 && RiseTime > 20)continue;
		// if(MaxPos/10000/3600 < 4.0)continue;
		if (Amp_raw < 0)
			continue;
		if (Amp_filtered < 0.0)
			continue;
		if (amp_filterfit < 0)
			continue;
		if (amp_rawfit < 0)
			continue;
		if (DecayTime < 10)
			continue;
		// if(RiseTime < 30)continue;
		// if(lstsq_rawfit > 52E3)continue;
		// if(Chi2filtered > 0.6)continue;
		// if(Amp_filtered < 0.00001)continue;
		// if(Amp_raw < 0.00001)continue;
		ene = amp_filterfit * Amp_filtered; //*511/129.2;
		// if(ene > 541)continue;
		// if(ene < 481)continue;
		// if(lstsq_rawfit > 52E4)continue;
		// if(lstsq_filterfit > 17)continue;
		// if(TMath::Abs(Amp_raw*511/129.2-Amp_filtered*amp_filterfit*511/129.2)>0.25*Amp_filtered*amp_filterfit*511/129.2)continue;
		// if(Chi2filtered > 0.85)continue;
		// if(Chi2filtered > 2)continue;
		// if(C > 1)continue;
		// if(Baseline > 0.5 && Amplitude < 10*Bl_RMS )continue;
		k1 += 1;
		// g1->SetPoint(k1, Baseline, amp_rawfit);
		g1->SetPoint(k1, Baseline, amp_filterfit * Amp_filtered);
		// g1->SetPoint(k1, Baseline, Amp_filtered);
		g2->SetPoint(k1, MaxPos / 3600. / 10000., Baseline);
		g3->SetPoint(k1, RiseTime, DecayTime);
		g4->SetPoint(k1, lstsq_rawfit, lstsq_filterfit);
		g5->SetPoint(k1, amp_rawfit, amp_filterfit);
		g6->SetPoint(k1, Chi2filtered, TVL);
		g7->SetPoint(k1, Chi2filtered, TVR);
		g8->SetPoint(k1, amp_filterfit * Amp_filtered, Chi2filtered);
		g9->SetPoint(k1, Amp_filtered, DecayTime);
		// hamp1->Fill(Amp_filtered*511/126.4);
		hamp1->Fill(Amp_raw / coeff);
		hamp2->Fill(amp_rawfit / coeff);
		hamp3->Fill(Amp_filtered / coeff);
		hamp4->Fill(Amp_filtered * amp_filterfit / coeff);
		hamp5->Fill(amp_rawfit / coeff);
		// hamp5->Fill(Amp_raw/coeff);
		tcut->Fill();
		// if(Amp_raw/coeff < 2.47)continue;
		// if(Amp_raw/coeff > 2.53)continue;
		outfile << setprecision(10) << MaxPos / 10000. + 0.5 << "," << Amp_filtered * amp_filterfit / coeff << "," << Amp_raw / coeff << endl;
		// outfile<<setprecision(10)<<MaxPos/10000.+0.5<<","<<Amp_filtered/coeff<<","<<amp_rawfit/coeff<<endl;
	}
	outfile.close();
	cout << "Total triggered:\t" << k1 << endl;
	tcut->Write();
	fcut->Close();
	/*
	 */
	TCanvas *c1 = new TCanvas("c1", "c1", 0, 0, 800, 600);
	g1->Draw("AP");
	g1->GetXaxis()->SetTitle("Baseline");
	g1->GetYaxis()->SetTitle("Amplitude");
	TCanvas *c2 = new TCanvas("c2", "c2", 0, 0, 800, 600);
	g2->Draw("AP");
	g2->GetXaxis()->SetTitle("Time (h)");
	g2->GetYaxis()->SetTitle("Baseline");
	TCanvas *c3 = new TCanvas("c3", "c3", 0, 0, 800, 600);
	g3->Draw("AP");
	g3->GetXaxis()->SetTitle("RiseTime");
	g3->GetYaxis()->SetTitle("DecayTime");
	TCanvas *c4 = new TCanvas("c4", "c4", 0, 0, 800, 600);
	g4->Draw("AP");
	g4->GetXaxis()->SetTitle("chi2_rawfit");
	g4->GetYaxis()->SetTitle("chi2_filterfit");
	TCanvas *c5 = new TCanvas("c5", "c5", 0, 0, 800, 600);
	g5->Draw("AP");
	g5->GetXaxis()->SetTitle("Amp_rawfit");
	g5->GetYaxis()->SetTitle("Amp_filterfit");
	TCanvas *c6 = new TCanvas("c6", "c6", 0, 0, 800, 600);
	g6->Draw("AP");
	g6->GetXaxis()->SetTitle("chi2_filtered");
	g6->GetYaxis()->SetTitle("TVL");
	TCanvas *c7 = new TCanvas("c7", "c7", 0, 0, 800, 600);
	g7->Draw("AP");
	g7->GetXaxis()->SetTitle("chi2_filtered");
	g7->GetYaxis()->SetTitle("TVR");
	TCanvas *c8 = new TCanvas("c8", "c8", 0, 0, 800, 600);
	g8->Draw("AP");
	g8->GetXaxis()->SetTitle("Amplitude");
	g8->GetYaxis()->SetTitle("Chi2Filtered");
	TCanvas *c9 = new TCanvas("c9", "c9", 0, 0, 800, 600);
	g9->Draw("AP");
	g9->GetXaxis()->SetTitle("Amplitude");
	g9->GetYaxis()->SetTitle("Decay Time");
	TCanvas *amp_spec1 = new TCanvas("amp_spec1", "", 0, 0, 800, 600);
	// hamp1->Scale(1.0/10.0);
	// hamp2->Scale(1.0/10.0);

	hamp1->Draw("HIST");
	hamp2->Draw("HIST SAME");
	hamp3->Draw("HIST SAME");
	hamp1->SetLineColor(kBlack);
	hamp3->SetLineColor(kRed);
	// hamp4->GetXaxis()->SetTitle("Amplitude");
	hamp1->GetXaxis()->SetTitle("Energy (ADC)");
	hamp1->GetYaxis()->SetTitle("Counts");
	/*
	hamp5->Draw("HIST SAME");
	hamp5->SetLineColor(kRed+2);
	hamp1->Draw("HIST");
	hamp2->Draw("HIST SAME");
	hamp3->Draw("HIST SAME");
	hamp4->Draw("HIST SAME");
	hamp2->SetLineColor(4);
	hamp3->SetLineColor(6);
	hamp4->SetLineColor(kRed);
	*/
	TLegend *leg1 = new TLegend(0.55, 0.65, 0.76, 0.82);
	leg1->AddEntry(hamp1, "Raw", "l");
	leg1->AddEntry(hamp2, "Raw_fit", "l");
	leg1->AddEntry(hamp3, "Filtered", "l");
	leg1->Draw();

	// 写入直方图和图形对象到 result.root
	f2->cd();
	hamp1->Write();
	hamp2->Write();
	hamp3->Write();
	hamp4->Write();
	hamp5->Write();

	g1->Write("g1");
	g2->Write("g2");
	g3->Write("g3");
	g4->Write("g4");
	g5->Write("g5");
	g6->Write("g6");
	g7->Write("g7");
	g8->Write("g8");
	g9->Write("g9");

	// 可选：也可以保存 canvas
	c1->Write("c1");
	c2->Write("c2");
	c3->Write("c3");
	c4->Write("c4");
	c5->Write("c5");
	c6->Write("c6");
	c7->Write("c7");
	c8->Write("c8");
	c9->Write("c9");
	amp_spec1->Write("amp_spec1");

	// 关闭文件，完成写入
	f2->Close();
	c1->Update(); c1->SaveAs("f/c1_Baseline_vs_Amplitude.png");
	c2->Update(); c2->SaveAs("f/c2_Time_vs_Baseline.png");
	c3->Update(); c3->SaveAs("f/c3_Rise_vs_Decay.png");
	c4->Update(); c4->SaveAs("f/c4_LstsqRaw_vs_Filter.png");
	c5->Update(); c5->SaveAs("f/c5_Rawfit_vs_Filterfit.png");
	c6->Update(); c6->SaveAs("f/c6_Chi2Filtered_vs_TVL.png");
	c7->Update(); c7->SaveAs("f/c7_Chi2Filtered_vs_TVR.png");
	c8->Update(); c8->SaveAs("f/c8_Amplitude_vs_Chi2Filtered.png");
	c9->Update(); c9->SaveAs("f/c9_FilteredAmp_vs_DecayTime.png");
	amp_spec1->Update(); amp_spec1->SaveAs("f/amp_spec1_AmplitudeSpectra.png");

	// hamp1->Write("Specwithwater");
	f2->Close();
}
