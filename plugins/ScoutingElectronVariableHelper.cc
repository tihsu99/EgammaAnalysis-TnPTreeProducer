#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/Candidate/interface/LeafCandidate.h"
#include "DataFormats/Common/interface/RefVector.h"
#include "DataFormats/Common/interface/ValueMap.h"
#include "DataFormats/Scouting/interface/Run3ScoutingElectron.h"
#include "DataFormats/Scouting/interface/Run3ScoutingVertex.h"

#include "EgammaAnalysis/TnPTreeProducer/plugins/WriteValueMap.h"

#include <algorithm>
#include <vector>

using LeafCandidateCollection = std::vector<reco::LeafCandidate>;

class ScoutingElectronVariableHelper : public edm::one::EDProducer<> {
public:
  explicit ScoutingElectronVariableHelper(const edm::ParameterSet& iConfig)
      : srcToken_(consumes<std::vector<Run3ScoutingElectron>>(iConfig.getParameter<edm::InputTag>("src"))),
        probesToken_(consumes<LeafCandidateCollection>(iConfig.getParameter<edm::InputTag>("probes"))),
        vtxToken_(consumes<std::vector<Run3ScoutingVertex>>(iConfig.getParameter<edm::InputTag>("vertexCollection"))),
        rhoToken_(consumes<double>(iConfig.getParameter<edm::InputTag>("rhoInputTag"))) {
    produces<edm::ValueMap<float>>("dEtaIn");
    produces<edm::ValueMap<float>>("dPhiIn");
    produces<edm::ValueMap<float>>("sigmaIetaIeta");
    produces<edm::ValueMap<float>>("hOverE");
    produces<edm::ValueMap<float>>("ooEMOop");
    produces<edm::ValueMap<float>>("missingHits");
    produces<edm::ValueMap<float>>("ecalIso");
    produces<edm::ValueMap<float>>("hcalIso");
    produces<edm::ValueMap<float>>("trackIso");
    produces<edm::ValueMap<float>>("r9");
    produces<edm::ValueMap<float>>("sMin");
    produces<edm::ValueMap<float>>("dxy");
    produces<edm::ValueMap<float>>("dz");
    produces<edm::ValueMap<float>>("sip");
    produces<edm::ValueMap<float>>("rho");
  }

  void produce(edm::Event& iEvent, const edm::EventSetup&) override {
    edm::Handle<std::vector<Run3ScoutingElectron>> src;
    edm::Handle<LeafCandidateCollection> probes;
    edm::Handle<std::vector<Run3ScoutingVertex>> vertices;
    edm::Handle<double> rhoH;

    iEvent.getByToken(srcToken_, src);
    iEvent.getByToken(probesToken_, probes);
    iEvent.getByToken(vtxToken_, vertices);
    iEvent.getByToken(rhoToken_, rhoH);

    const float rho = rhoH.isValid() ? *rhoH : 999999.f;

    std::vector<float> dEtaIn;
    std::vector<float> dPhiIn;
    std::vector<float> sigmaIetaIeta;
    std::vector<float> hOverE;
    std::vector<float> ooEMOop;
    std::vector<float> missingHits;
    std::vector<float> ecalIso;
    std::vector<float> hcalIso;
    std::vector<float> trackIso;
    std::vector<float> r9;
    std::vector<float> sMin;
    std::vector<float> dxy;
    std::vector<float> dz;
    std::vector<float> sip;
    std::vector<float> rhoVals;

    const size_t n = std::min(src->size(), probes->size());
    dEtaIn.reserve(n);
    dPhiIn.reserve(n);
    sigmaIetaIeta.reserve(n);
    hOverE.reserve(n);
    ooEMOop.reserve(n);
    missingHits.reserve(n);
    ecalIso.reserve(n);
    hcalIso.reserve(n);
    trackIso.reserve(n);
    r9.reserve(n);
    sMin.reserve(n);
    dxy.reserve(n);
    dz.reserve(n);
    sip.reserve(n);
    rhoVals.reserve(n);

    for (size_t i = 0; i < n; ++i) {
      const auto& ele = (*src)[i];
      dEtaIn.push_back(ele.dEtaIn());
      dPhiIn.push_back(ele.dPhiIn());
      sigmaIetaIeta.push_back(ele.sigmaIetaIeta());
      hOverE.push_back(ele.hOverE());
      ooEMOop.push_back(ele.ooEMOop());
      missingHits.push_back(ele.missingHits());
      ecalIso.push_back(ele.ecalIso());
      hcalIso.push_back(ele.hcalIso());
      trackIso.push_back(ele.trackIso());
      r9.push_back(ele.r9());
      sMin.push_back(ele.sMin());
      dxy.push_back(ele.trkd0().empty() ? 999999.f : ele.trkd0()[0]);
      dz.push_back(ele.trkdz().empty() ? 999999.f : ele.trkdz()[0]);
      sip.push_back(999999.f);
      rhoVals.push_back(rho);
    }

    writeValueMap(iEvent, probes, dEtaIn, "dEtaIn");
    writeValueMap(iEvent, probes, dPhiIn, "dPhiIn");
    writeValueMap(iEvent, probes, sigmaIetaIeta, "sigmaIetaIeta");
    writeValueMap(iEvent, probes, hOverE, "hOverE");
    writeValueMap(iEvent, probes, ooEMOop, "ooEMOop");
    writeValueMap(iEvent, probes, missingHits, "missingHits");
    writeValueMap(iEvent, probes, ecalIso, "ecalIso");
    writeValueMap(iEvent, probes, hcalIso, "hcalIso");
    writeValueMap(iEvent, probes, trackIso, "trackIso");
    writeValueMap(iEvent, probes, r9, "r9");
    writeValueMap(iEvent, probes, sMin, "sMin");
    writeValueMap(iEvent, probes, dxy, "dxy");
    writeValueMap(iEvent, probes, dz, "dz");
    writeValueMap(iEvent, probes, sip, "sip");
    writeValueMap(iEvent, probes, rhoVals, "rho");
  }

private:
  edm::EDGetTokenT<std::vector<Run3ScoutingElectron>> srcToken_;
  edm::EDGetTokenT<LeafCandidateCollection> probesToken_;
  edm::EDGetTokenT<std::vector<Run3ScoutingVertex>> vtxToken_;
  edm::EDGetTokenT<double> rhoToken_;
};

DEFINE_FWK_MODULE(ScoutingElectronVariableHelper);
