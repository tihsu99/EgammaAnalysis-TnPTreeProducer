#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/Exception.h"

#include "DataFormats/Candidate/interface/LeafCandidate.h"
#include "DataFormats/Common/interface/RefVector.h"
#include "DataFormats/Scouting/interface/Run3ScoutingElectron.h"

#include <cmath>
#include <vector>

using LeafCandidateCollection = std::vector<reco::LeafCandidate>;
using LeafCandidateRefVector = edm::RefVector<LeafCandidateCollection>;

class ScoutingElectronRefSelector : public edm::one::EDProducer<> {
public:
  explicit ScoutingElectronRefSelector(const edm::ParameterSet& iConfig)
      : inputToken_(consumes<LeafCandidateRefVector>(iConfig.getParameter<edm::InputTag>("input"))),
        srcToken_(consumes<std::vector<Run3ScoutingElectron>>(iConfig.getParameter<edm::InputTag>("src"))),
        workingPoint_(iConfig.getParameter<std::string>("workingPoint")) {
    produces<LeafCandidateRefVector>();
  }

  void produce(edm::Event& iEvent, const edm::EventSetup&) override {
    edm::Handle<LeafCandidateRefVector> input;
    edm::Handle<std::vector<Run3ScoutingElectron>> src;
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
  bool passWorkingPoint(const Run3ScoutingElectron& ele) const {
    if (workingPoint_ == "ScoutingElectronRecommendv1") {
      return passScoutingElectronRecommendv1(ele);
    }
    if (workingPoint_ == "ScoutingElectronCustomizev1") {
      return passScoutingElectronCustomizev1(ele);
    }
    if (workingPoint_ == "ScoutingPhotonRecommendv1") {
      return passScoutingPhotonRecommendv1(ele);
    }
    if (workingPoint_ == "ScoutingPhotonCustomizev1") {
      return passScoutingPhotonCustomizev1(ele);
    }
    throw cms::Exception("Configuration")
        << "Unknown scouting electron working point: " << workingPoint_;
  }

  bool passScoutingElectronRecommendv1(const Run3ScoutingElectron& ele) const {
    const float energy = std::max(1.f, static_cast<float>(ele.pt() * std::cosh(ele.eta())));
    if (std::abs(ele.eta()) < 1.479f) {
      return (ele.sigmaIetaIeta() < 0.015f) && (ele.hOverE() < 0.2f) && (std::abs(ele.dEtaIn()) < 0.008f) &&
             (std::abs(ele.dPhiIn()) < 0.06f) && ((ele.ecalIso() / energy) < 0.25f) && ((ele.trackIso() / energy) < 0.001f);
    } else {
      return (ele.sigmaIetaIeta() < 0.045f) && (ele.hOverE() < 0.2f) && (std::abs(ele.dEtaIn()) < 0.012f) &&
             (std::abs(ele.dPhiIn()) < 0.06f) && ((ele.ecalIso() / energy) < 0.1f) && ((ele.trackIso() / energy) < 0.001f);
    }
  }

  bool passScoutingElectronCustomizev1(const Run3ScoutingElectron& ele) const {
    const float energy = std::max(1.f, static_cast<float>(ele.pt() * std::cosh(ele.eta())));
    if (!passScoutingElectronRecommendv1(ele)) {
      return false;
    }
    if (std::abs(ele.eta()) < 1.479f) {
      return (ele.hcalIso() / energy) < 0.4f;
    } else {
      return (ele.hcalIso() / energy) < 0.6f;
    }
  }

  bool passScoutingPhotonRecommendv1(const Run3ScoutingElectron& ele) const {
    const float energy = std::max(1.f, static_cast<float>(ele.pt() * std::cosh(ele.eta())));
    if (std::abs(ele.eta()) < 1.479f) {
      return (ele.sigmaIetaIeta() < 0.015f) && (ele.hOverE() < 0.2f) && ((ele.ecalIso() / energy) < 0.25f);
    } else {
      return (ele.sigmaIetaIeta() < 0.045f) && (ele.hOverE() < 0.2f) && ((ele.ecalIso() / energy) < 0.1f);
    }
  }

  bool passScoutingPhotonCustomizev1(const Run3ScoutingElectron& ele) const {
    const float energy = std::max(1.f, static_cast<float>(ele.pt() * std::cosh(ele.eta())));
    if (!passScoutingPhotonRecommendv1(ele)) {
      return false;
    }
    if (std::abs(ele.eta()) < 1.479f) {
      return (ele.hcalIso() / energy) < 0.6f;
    } else {
      return (ele.hcalIso() / energy) < 1.0f;
    }
  }


  edm::EDGetTokenT<LeafCandidateRefVector> inputToken_;
  edm::EDGetTokenT<std::vector<Run3ScoutingElectron>> srcToken_;
  std::string workingPoint_;
};

DEFINE_FWK_MODULE(ScoutingElectronRefSelector);
