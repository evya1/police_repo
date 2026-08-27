"""Series-scoped transport composition for the Police peer."""

from common.transport.greetings import NegotiationContext, SeriesGreetingSession
from common.transport.opponent_pin import OpponentPin
from common.transport.series import PeerFacade
from police_peer.live_events import observe_driver
from police_peer.wire.negotiate_per_subgame import negotiated_subgame_driver


def compose_series_peer(
    *, channel, engine, config, group_id: str, mode: str, audit_wire, listener,
) -> PeerFacade:
    """Create the one opponent pin and greeting session owned by this series."""
    opponent_pin = OpponentPin()
    greetings = SeriesGreetingSession(NegotiationContext(
        terms=config.terms,
        group_id=group_id,
        locks=config.locks,
        identity_block=config.identity_block,
    ))
    driver = negotiated_subgame_driver(
        group_id, opponent_pin=opponent_pin, audit_wire=audit_wire,
        greeting_session=greetings,
    )
    return PeerFacade(
        channel=channel,
        engine=engine,
        config=config,
        name=group_id,
        mode=mode,
        opponent_pin=opponent_pin,
        greeting_session=greetings,
        subgame_driver=observe_driver(driver, listener),
    )
