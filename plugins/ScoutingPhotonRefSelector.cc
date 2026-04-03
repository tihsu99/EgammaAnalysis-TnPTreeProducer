#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/Exception.h"

#include "DataFormats/Candidate/interface/LeafCandidate.h"
#include "DataFormats/Common/interface/RefVector.h"
#include "DataFormats/Scouting/interface/Run3ScoutingPhoton.h"

#include <cmath>
#include <vector>

using LeafCandidateCollection = std::vector<reco::LeafCandidate>;
using LeafCandidateRefVector = edm::RefVector<LeafCandidateCollection>;

class ScoutingPhotonRefSelector : public edm::one::EDProducer<> {
public:
  explicit ScoutingPhotonRefSelector(const edm::ParameterSet& iConfig)
      : inputToken_(consumes<LeafCandidateRefVector>(iConfig.getParameter<edm::InputTag>("input"))),
        srcToken_(consumes<std::vector<Run3ScoutingPhoton>>(iConfig.getParameter<edm::InputTag>("src"))),
        workingPoint_(iConfig.getParameter<std::string>("workingPoint")) {
    produces<LeafCandidateRefVector>();
  }

  void produce(edm::Event& iEvent, const edm::EventSetup&) override {
    edm::Handle<LeafCandidateRefVector> input;
    edm::Handle<std::vector<Run3ScoutingPhoton>> src;
    iEvent.getByToken(inputToken_, input);
    iEvent.getByToken(srcToken_, src);

    auto out = std::make_unique<LeafCandidateRefVector>();
    if (!input.isValid() || !src.isValid()) {
      iEvent.put(std::move(out));
      return;
    }

    for (const auto& ref : *input) {
      if (ref.isNull()) {
        continue;
      }
      const auto index = ref.key();
      if (index >= src->size()) {
        continue;
      }
      if (passWorkingPoint((*src)[index])) {
        out->push_back(ref);
      }
    }

    iEvent.put(std::move(out));
  }

private:
  bool passWorkingPoint(const Run3ScoutingPhoton& pho) const {
    if (workingPoint_ == "ScoutingPhotonRecommendv1") {
      return passScoutingPhotonRecommendv1(pho);
     }
    throw cms::Exception("Configuration")
        << "Unknown scouting photon working point: " << workingPoint_;
  }

  bool passScoutingPhotonRecommendv1(const Run3ScoutingPhoton& pho) const {
    const float energy = std::max(1.f, static_cast<float>(pho.pt() * std::cosh(pho.eta())));
    if (std::abs(pho.eta()) < 1.479f) {
      return (pho.sigmaIetaIeta() < 0.015f) && (pho.hOverE() < 0.2f) && ((pho.ecalIso() / energy) < 0.25f);
    } else {
      return (pho.sigmaIetaIeta() < 0.045f) && (pho.hOverE() < 0.2f) && ((pho.ecalIso() / energy) < 0.1f);
    }
  }



  edm::EDGetTokenT<LeafCandidateRefVector> inputToken_;
  edm::EDGetTokenT<std::vector<Run3ScoutingPhoton>> srcToken_;
  std::string workingPoint_;
};

DEFINE_FWK_MODULE(ScoutingPhotonRefSelector);
