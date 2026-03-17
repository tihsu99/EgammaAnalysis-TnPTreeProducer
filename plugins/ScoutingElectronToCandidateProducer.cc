#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/Candidate/interface/LeafCandidate.h"
#include "DataFormats/Math/interface/LorentzVector.h"
#include "DataFormats/Math/interface/Point3D.h"
#include "DataFormats/Scouting/interface/Run3ScoutingElectron.h"
#include "Math/Vector4D.h"

class ScoutingElectronToCandidateProducer : public edm::one::EDProducer<> {
public:
  explicit ScoutingElectronToCandidateProducer(const edm::ParameterSet& iConfig)
      : srcToken_(consumes<std::vector<Run3ScoutingElectron>>(iConfig.getParameter<edm::InputTag>("src"))) {
    produces<reco::LeafCandidateCollection>();
  }

  void produce(edm::Event& iEvent, const edm::EventSetup&) override {
    edm::Handle<std::vector<Run3ScoutingElectron>> src;
    iEvent.getByToken(srcToken_, src);

    auto out = std::make_unique<reco::LeafCandidateCollection>();
    out->reserve(src->size());

    for (const auto& ele : *src) {
      reco::LeafCandidate cand;
      const math::PtEtaPhiMLorentzVector p4(ele.pt(), ele.eta(), ele.phi(), ele.m());
      const reco::Particle::LorentzVector recoP4(p4.px(), p4.py(), p4.pz(), p4.energy());
      cand.setP4(recoP4);
      cand.setCharge(ele.charge());
      cand.setVertex(reco::Candidate::Point(0., 0., 0.));
      cand.setPdgId(ele.charge() < 0 ? 11 : -11);
      out->push_back(cand);
    }

    iEvent.put(std::move(out));
  }

private:
  edm::EDGetTokenT<std::vector<Run3ScoutingElectron>> srcToken_;
};

DEFINE_FWK_MODULE(ScoutingElectronToCandidateProducer);
