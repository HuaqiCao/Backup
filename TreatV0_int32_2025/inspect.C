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
#include <Math/Interpolator.h>
using namespace TMath;
void inspect(){
    gROOT->ProcessLine(".L ~/WorkArea/Bolometer/Program/Tool_Package/tool/plotstyle/bes3plotstyle.C");
    SetStyle();
    SetPrelimStyle();
    Int_t start_pos = 1119000;
    Int_t length = 20000;
    Int_t wl = 3000;
    Int_t samplefreq=10000;
    std::ifstream inf_bi("/Volumes/Kangkang/Lab104/0701_data/LMO_Na22_1700gain_200Mohm_2Vbias_1Vrange_water_0701.BIN4", std::ios::binary); // 打开二进制文件
    if (!inf_bi) {
        std::cerr << "cant open file"<<endl;
        return 1;
    }
    // 设置文件指针的位置为第xxx个字节
    inf_bi.seekg((start_pos+wl/2)*4, std::ios::beg);
    TH1D *data_win = new TH1D("data_win","Data in the fitting windowi;Time (s);Height (ADC)",length,0,length*1.0/samplefreq);
    // 读取文件中的数据
    char buffer[4];
    Int_t k = 0;
    int value = 0;
    int start_value = 0;
    while (k < length){
        inf_bi.read(buffer, sizeof(buffer));
        // 将读取到的二进制数据转换为整型数据
        //unsigned short value = (static_cast<unsigned char>(buffer[1]) << 8) | static_cast<unsigned char>(buffer[0]);
        // 将读取到的二进制数据转换为浮点型数据
        std::memcpy(&value, buffer, 4);//sizeof(float));
        if(k<1){
            start_value = value;
        }
        data_win->SetBinContent(k+1, value-start_value);
        k += 1;
    }
    std::ifstream inf_bi_filter("/Volumes/Kangkang/Lab104/0701_data/data/diff_filtereddata.BIN2", std::ios::binary); // 打开二进制文件
    if (!inf_bi_filter) {
        std::cerr << "cant open file"<<endl;
        return 1;
    }
    // 设置文件指针的位置为第xxx个字节
    inf_bi_filter.seekg((start_pos)*4, std::ios::beg);
    TH1D *data_win_filter = new TH1D("data_win_filter","Data in the fitting window",length,0,length*1.0/samplefreq);
    // 读取文件中的数据
    char buffer_filter[4];
    k = 0;
    float value_filter=0.0;
    while (k < length){
        inf_bi_filter.read(buffer_filter, sizeof(buffer_filter));
        // 将读取到的二进制数据转换为浮点型数据
        std::memcpy(&value_filter, buffer_filter, sizeof(float));
        data_win_filter->SetBinContent(k+1, value_filter);
        k += 1;
    }
    TCanvas *c2 = new TCanvas("c2", "c2", 0, 0, 1200, 600);
    data_win->Draw();
    data_win_filter->Draw("SAME");
    //data_win_filter->Draw("");
    data_win->SetLineColor(kBlue+0);
    data_win_filter->SetLineColor(kRed+0);
}
