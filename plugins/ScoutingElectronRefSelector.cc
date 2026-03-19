#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/Exception.h"

#include "DataFormats/Candidate/interface/LeafCandidate.h"
#include "DataFormats/Common/interface/RefVector.h"
#include "DataFormats/Scouting/interface/Run3ScoutingElectron.h"

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
    if (workingPoint_ == "ScoutingHoE0p20") {
      return passScoutingHoE0p20(ele);
    }
    if (workingPoint_ == "ScoutingPlaceholderWP") {
      return passScoutingPlaceholderWP(ele);
    }
    if (workingPoint_ == "ScoutingLoose") {
      return passScoutingLoose(ele);
    }
    if (workingPoint_ == "ScoutingMedium") {
      return passScoutingMedium(ele);
    }
    if (workingPoint_ == "ScoutingTight") {
      return passScoutingTight(ele);
    }

    throw cms::Exception("Configuration")
        << "Unknown scouting electron working point: " << workingPoint_;
  }

  bool passScoutingHoE0p20(const Run3ScoutingElectron& ele) const { return ele.hOverE() < 0.2f; }

  bool passScoutingPlaceholderWP(const Run3ScoutingElectron& ele) const {
    // Placeholder scouting WP. Replace this recipe with the desired selection.
    return ele.hOverE() < 0.2f;
  }

  bool passScoutingLoose(const Run3ScoutingElectron& ele) const {
    // Placeholder loose scouting ID.
    return ele.hOverE() < 0.2f;
  }

  bool passScoutingMedium(const Run3ScoutingElectron& ele) const {
    // Placeholder medium scouting ID.
    return ele.hOverE() < 0.2f;
  }

  bool passScoutingTight(const Run3ScoutingElectron& ele) const {
    // Placeholder tight scouting ID.
    return ele.hOverE() < 0.2f;
  }

  edm::EDGetTokenT<LeafCandidateRefVector> inputToken_;
  edm::EDGetTokenT<std::vector<Run3ScoutingElectron>> srcToken_;
  std::string workingPoint_;
};

DEFINE_FWK_MODULE(ScoutingElectronRefSelector);
