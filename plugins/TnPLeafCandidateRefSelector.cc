#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "CommonTools/Utils/interface/StringCutObjectSelector.h"

#include "DataFormats/Candidate/interface/LeafCandidate.h"
#include "DataFormats/Candidate/interface/LeafCandidateFwd.h"

class TnPLeafCandidateRefSelector : public edm::one::EDProducer<> {
public:
  explicit TnPLeafCandidateRefSelector(const edm::ParameterSet& iConfig)
      : srcToken_(consumes<reco::LeafCandidateCollection>(iConfig.getParameter<edm::InputTag>("src"))),
        selector_(iConfig.getParameter<std::string>("cut")) {
    produces<reco::LeafCandidateRefVector>();
  }

  void produce(edm::Event& iEvent, const edm::EventSetup&) override {
    edm::Handle<reco::LeafCandidateCollection> src;
    iEvent.getByToken(srcToken_, src);

    auto out = std::make_unique<reco::LeafCandidateRefVector>();
    for (size_t i = 0; i < src->size(); ++i) {
      reco::LeafCandidateRef ref(src, i);
      if (selector_(*ref)) {
        out->push_back(ref);
      }
    }

    iEvent.put(std::move(out));
  }

private:
  edm::EDGetTokenT<reco::LeafCandidateCollection> srcToken_;
  StringCutObjectSelector<reco::LeafCandidate> selector_;
};

DEFINE_FWK_MODULE(TnPLeafCandidateRefSelector);
