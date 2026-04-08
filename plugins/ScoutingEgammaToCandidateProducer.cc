#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/Candidate/interface/LeafCandidate.h"
#include "DataFormats/Common/interface/ValueMap.h"
#include "DataFormats/Scouting/interface/Run3ScoutingElectron.h"
#include "DataFormats/Scouting/interface/Run3ScoutingPhoton.h"
#include "Math/Vector4D.h"

#include <vector>

using LeafCandidateCollection = std::vector<reco::LeafCandidate>;

class ScoutingEgammaToCandidateProducer : public edm::one::EDProducer<> {
public:
  explicit ScoutingEgammaToCandidateProducer(const edm::ParameterSet& iConfig)
      : electronsToken_(consumes<std::vector<Run3ScoutingElectron>>(iConfig.getParameter<edm::InputTag>("electrons"))),
        photonsToken_(consumes<std::vector<Run3ScoutingPhoton>>(iConfig.getParameter<edm::InputTag>("photons"))),
        bestTrackChargeToken_(consumes<edm::ValueMap<int>>(iConfig.getParameter<edm::InputTag>("bestTrackCharge"))) {
    produces<LeafCandidateCollection>();
  }

  void produce(edm::Event& iEvent, const edm::EventSetup&) override {
    edm::Handle<std::vector<Run3ScoutingElectron>> electrons;
    edm::Handle<std::vector<Run3ScoutingPhoton>> photons;
    edm::Handle<edm::ValueMap<int>> bestTrackCharge;
    iEvent.getByToken(electronsToken_, electrons);
    iEvent.getByToken(photonsToken_, photons);
    iEvent.getByToken(bestTrackChargeToken_, bestTrackCharge);

    auto out = std::make_unique<LeafCandidateCollection>();
    out->reserve(electrons->size() + photons->size());

    for (size_t i = 0; i < electrons->size(); ++i) {
      const auto& ele = (*electrons)[i];
      reco::LeafCandidate cand;
      const math::PtEtaPhiMLorentzVector p4(ele.pt(), ele.eta(), ele.phi(), ele.m());
      const reco::Particle::LorentzVector recoP4(p4.px(), p4.py(), p4.pz(), p4.energy());
      int charge = ele.trkcharge().empty() ? 0 : ele.trkcharge()[0];
      if (bestTrackCharge.isValid()) {
        const edm::Ref<std::vector<Run3ScoutingElectron>> eleRef(electrons, i);
        charge = (*bestTrackCharge)[eleRef];
      }
      cand.setP4(recoP4);
      cand.setCharge(charge);
      cand.setVertex(reco::Candidate::Point(0., 0., 0.));
      cand.setPdgId(charge < 0 ? 11 : -11);
      out->push_back(cand);
    }

    for (const auto& pho : *photons) {
      reco::LeafCandidate cand;
      const math::PtEtaPhiMLorentzVector p4(pho.pt(), pho.eta(), pho.phi(), pho.m());
      const reco::Particle::LorentzVector recoP4(p4.px(), p4.py(), p4.pz(), p4.energy());
      cand.setP4(recoP4);
      cand.setCharge(0);
      cand.setVertex(reco::Candidate::Point(0., 0., 0.));
      cand.setPdgId(22);
      out->push_back(cand);
    }

    iEvent.put(std::move(out));
  }

private:
  edm::EDGetTokenT<std::vector<Run3ScoutingElectron>> electronsToken_;
  edm::EDGetTokenT<std::vector<Run3ScoutingPhoton>> photonsToken_;
  edm::EDGetTokenT<edm::ValueMap<int>> bestTrackChargeToken_;
};

DEFINE_FWK_MODULE(ScoutingEgammaToCandidateProducer);
