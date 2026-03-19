#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/Candidate/interface/LeafCandidate.h"
#include "DataFormats/Common/interface/ValueMap.h"
#include "DataFormats/Math/interface/LorentzVector.h"
#include "DataFormats/Math/interface/Point3D.h"
#include "DataFormats/Scouting/interface/Run3ScoutingElectron.h"
#include "Math/Vector4D.h"

#include <vector>

using LeafCandidateCollection = std::vector<reco::LeafCandidate>;

class ScoutingElectronToCandidateProducer : public edm::one::EDProducer<> {
public:
  explicit ScoutingElectronToCandidateProducer(const edm::ParameterSet& iConfig)
      : srcToken_(consumes<std::vector<Run3ScoutingElectron>>(iConfig.getParameter<edm::InputTag>("src"))),
        bestTrackChargeToken_(consumes<edm::ValueMap<int>>(iConfig.getParameter<edm::InputTag>("bestTrackCharge"))) {
    produces<LeafCandidateCollection>();
  }

  void produce(edm::Event& iEvent, const edm::EventSetup&) override {
    edm::Handle<std::vector<Run3ScoutingElectron>> src;
    edm::Handle<edm::ValueMap<int>> bestTrackCharge;
    iEvent.getByToken(srcToken_, src);
    iEvent.getByToken(bestTrackChargeToken_, bestTrackCharge);

    auto out = std::make_unique<LeafCandidateCollection>();
    out->reserve(src->size());

    for (size_t i = 0; i < src->size(); ++i) {
      const auto& ele = (*src)[i];
      reco::LeafCandidate cand;
      const math::PtEtaPhiMLorentzVector p4(ele.pt(), ele.eta(), ele.phi(), ele.m());
      const reco::Particle::LorentzVector recoP4(p4.px(), p4.py(), p4.pz(), p4.energy());
      int charge = ele.trkcharge().empty() ? 0 : ele.trkcharge()[0];
      if (bestTrackCharge.isValid()) {
        const edm::Ref<std::vector<Run3ScoutingElectron>> eleRef(src, i);
        charge = (*bestTrackCharge)[eleRef];
      }
      cand.setP4(recoP4);
      cand.setCharge(charge);
      cand.setVertex(reco::Candidate::Point(0., 0., 0.));
      cand.setPdgId(charge < 0 ? 11 : -11);
      out->push_back(cand);
    }

    iEvent.put(std::move(out));
  }

private:
  edm::EDGetTokenT<std::vector<Run3ScoutingElectron>> srcToken_;
  edm::EDGetTokenT<edm::ValueMap<int>> bestTrackChargeToken_;
};

DEFINE_FWK_MODULE(ScoutingElectronToCandidateProducer);
