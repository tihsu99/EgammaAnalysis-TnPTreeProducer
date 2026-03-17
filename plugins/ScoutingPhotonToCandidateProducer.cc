#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/Candidate/interface/LeafCandidate.h"
#include "DataFormats/Scouting/interface/Run3ScoutingPhoton.h"
#include "Math/Vector4D.h"

class ScoutingPhotonToCandidateProducer : public edm::one::EDProducer<> {
public:
  explicit ScoutingPhotonToCandidateProducer(const edm::ParameterSet& iConfig)
      : srcToken_(consumes<std::vector<Run3ScoutingPhoton>>(iConfig.getParameter<edm::InputTag>("src"))) {
    produces<reco::LeafCandidateCollection>();
  }

  void produce(edm::Event& iEvent, const edm::EventSetup&) override {
    edm::Handle<std::vector<Run3ScoutingPhoton>> src;
    iEvent.getByToken(srcToken_, src);

    auto out = std::make_unique<reco::LeafCandidateCollection>();
    out->reserve(src->size());

    for (const auto& pho : *src) {
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
  edm::EDGetTokenT<std::vector<Run3ScoutingPhoton>> srcToken_;
};

DEFINE_FWK_MODULE(ScoutingPhotonToCandidateProducer);
