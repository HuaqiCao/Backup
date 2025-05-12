//////////////////////////////////////////////////////////
// This class has been automatically generated on
// Tue Jun 27 17:30:36 2023 by ROOT version 6.24/06
// from TTree tree1/
// found on file: ../data/TriggerEvent.root
//////////////////////////////////////////////////////////

#ifndef myclass_h
#define myclass_h

#include <TROOT.h>
#include <TChain.h>
#include <TFile.h>

// Header file for the classes stored in the TTree if any.

class myclass {
public :
   TTree          *fChain;   //!pointer to the analyzed TTree or TChain
   Int_t           fCurrent; //!current Tree number in a TChain

// Fixed size dimensions of array or collections stored in the TTree if any.

   // Declaration of leaf types
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

   // List of branches
   TBranch        *b_MaxPos;   //!
   TBranch        *b_Baseline;   //!
   TBranch        *b_Amp_raw;   //!
   TBranch        *b_Amp_filtered;   //!
   TBranch        *b_RiseTime;   //!
   TBranch        *b_DecayTime;   //!
   TBranch        *b_TVL;   //!
   TBranch        *b_TVR;   //!
   TBranch        *b_Chi2raw;   //!
   TBranch        *b_Chi2filtered;   //!
   TBranch        *b_amp_rawfit;   //!
   TBranch        *b_bl_rawfit;   //!
   TBranch        *b_lstsq_rawfit;   //!
   TBranch        *b_amp_filterfit;   //!
   TBranch        *b_bl_filterfit;   //!
   TBranch        *b_lstsq_filterfit;   //!
   TBranch        *b_bl_RMS;   //!
   TBranch        *b_bl_slope;   //!
   TBranch        *b_bl_chi2;   //!

   myclass(TTree *tree=0);
   virtual ~myclass();
   virtual Int_t    Cut(Long64_t entry);
   virtual Int_t    GetEntry(Long64_t entry);
   virtual Long64_t LoadTree(Long64_t entry);
   virtual void     Init(TTree *tree);
   virtual void     Loop();
   virtual Bool_t   Notify();
   virtual void     Show(Long64_t entry = -1);
};

#endif

#ifdef myclass_cxx
myclass::myclass(TTree *tree) : fChain(0) 
{
// if parameter tree is not specified (or zero), connect the file
// used to generate this class and read the Tree.
   if (tree == 0) {
      TFile *f = (TFile*)gROOT->GetListOfFiles()->FindObject("../data/TriggerEvent.root");
      if (!f || !f->IsOpen()) {
         f = new TFile("../data/TriggerEvent.root");
      }
      f->GetObject("tree1",tree);

   }
   Init(tree);
}

myclass::~myclass()
{
   if (!fChain) return;
   delete fChain->GetCurrentFile();
}

Int_t myclass::GetEntry(Long64_t entry)
{
// Read contents of entry.
   if (!fChain) return 0;
   return fChain->GetEntry(entry);
}
Long64_t myclass::LoadTree(Long64_t entry)
{
// Set the environment to read one entry
   if (!fChain) return -5;
   Long64_t centry = fChain->LoadTree(entry);
   if (centry < 0) return centry;
   if (fChain->GetTreeNumber() != fCurrent) {
      fCurrent = fChain->GetTreeNumber();
      Notify();
   }
   return centry;
}

void myclass::Init(TTree *tree)
{
   // The Init() function is called when the selector needs to initialize
   // a new tree or chain. Typically here the branch addresses and branch
   // pointers of the tree will be set.
   // It is normally not necessary to make changes to the generated
   // code, but the routine can be extended by the user if needed.
   // Init() will be called many times when running on PROOF
   // (once per file to be processed).

   // Set branch addresses and branch pointers
   if (!tree) return;
   fChain = tree;
   fCurrent = -1;
   fChain->SetMakeClass(1);

   fChain->SetBranchAddress("MaxPos", &MaxPos, &b_MaxPos);
   fChain->SetBranchAddress("Baseline", &Baseline, &b_Baseline);
   fChain->SetBranchAddress("Amp_raw", &Amp_raw, &b_Amp_raw);
   fChain->SetBranchAddress("Amp_filtered", &Amp_filtered, &b_Amp_filtered);
   fChain->SetBranchAddress("RiseTime", &RiseTime, &b_RiseTime);
   fChain->SetBranchAddress("DecayTime", &DecayTime, &b_DecayTime);
   fChain->SetBranchAddress("TVL", &TVL, &b_TVL);
   fChain->SetBranchAddress("TVR", &TVR, &b_TVR);
   fChain->SetBranchAddress("Chi2raw", &Chi2raw, &b_Chi2raw);
   fChain->SetBranchAddress("Chi2filtered", &Chi2filtered, &b_Chi2filtered);
   fChain->SetBranchAddress("amp_rawfit", &amp_rawfit, &b_amp_rawfit);
   fChain->SetBranchAddress("bl_rawfit", &bl_rawfit, &b_bl_rawfit);
   fChain->SetBranchAddress("lstsq_rawfit", &lstsq_rawfit, &b_lstsq_rawfit);
   fChain->SetBranchAddress("amp_filterfit", &amp_filterfit, &b_amp_filterfit);
   fChain->SetBranchAddress("bl_filterfit", &bl_filterfit, &b_bl_filterfit);
   fChain->SetBranchAddress("lstsq_filterfit", &lstsq_filterfit, &b_lstsq_filterfit);
   fChain->SetBranchAddress("bl_RMS", &bl_RMS, &b_bl_RMS);
   fChain->SetBranchAddress("bl_slope", &bl_slope, &b_bl_slope);
   fChain->SetBranchAddress("bl_chi2", &bl_chi2, &b_bl_chi2);
   Notify();
}

Bool_t myclass::Notify()
{
   // The Notify() function is called when a new file is opened. This
   // can be either for a new TTree in a TChain or when when a new TTree
   // is started when using PROOF. It is normally not necessary to make changes
   // to the generated code, but the routine can be extended by the
   // user if needed. The return value is currently not used.

   return kTRUE;
}

void myclass::Show(Long64_t entry)
{
// Print contents of entry.
// If entry is not specified, print current entry
   if (!fChain) return;
   fChain->Show(entry);
}
Int_t myclass::Cut(Long64_t entry)
{
// This function may be called from Loop.
// returns  1 if entry is accepted.
// returns -1 otherwise.
   return 1;
}
#endif // #ifdef myclass_cxx
